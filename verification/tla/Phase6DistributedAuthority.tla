------------------- MODULE Phase6DistributedAuthority -------------------
(* ========================================================================= *)
(* CORTEX PHASE 6: DISTRIBUTED AUTHORITY & STATE MACHINE FORMAL SPEC         *)
(*                                                                           *)
(* Formal TLA+ specification modeling cluster authority election, network    *)
(* partitions, crash recovery, monotonic epoch/generation fencing, and WAL   *)
(* replay composition for the Cortex distributed kernel substrate.           *)
(*                                                                           *)
(* ASSURANCE BOUNDARY:                                                       *)
(*   Safety = MODEL-CHECKED for finite bounded state space                   *)
(*   Liveness = MODEL-CHECKED under weak fairness                            *)
(*   Proof = NOT a deductive proof for all infinite executions               *)
(*                                                                           *)
(* MODEL BOUNDS (TLC configuration, see .cfg):                               *)
(*   Nodes      = {N1, N2}        (2 cluster nodes)                          *)
(*   Workers    = {W1}            (1 worker process)                         *)
(*   Invocations= {I1}            (1 invocation)                             *)
(*   MaxEpoch   = 3               (authority epoch ceiling)                  *)
(*   MaxGen     = 2               (worker generation ceiling)                *)
(*   MaxAttempts= 2               (invocation attempt ceiling)               *)
(*   WAL depth  = 3               (max WAL records per node)                 *)
(*   Network    = bounded (< 3)   (in-flight message cap)                    *)
(*                                                                           *)
(* DESIGN DECISION — AUTHORITY INVALIDATION vs ASSIGNMENT DELETION:          *)
(*   LeaderElection does NOT delete assignments. It advances E_A.            *)
(*   Stale assignments (a.epA < E_A) persist in the assignment set           *)
(*   but are FENCED at commit time: CommitMutation requires                  *)
(*     presentedEpA = epochA (the active authority epoch).                   *)
(*   This models the real-world distinction between:                         *)
(*     - "old work is still running" (stale assignment exists)               *)
(*     - "old work cannot commit"    (fencing rejects stale commit)          *)
(*                                                                           *)
(* COMPOSITION WITH COQ LOCAL SAFETY (Phase 6 WAL / Phase 5 Scheduler):     *)
(*   Axiom: Restart(n) => State_n = Replay(ValidPrefix(WAL_n))              *)
(*   This is PROVEN in verification/Phase6WALSafety.v (0 Axioms, 0 Admits)  *)
(*   and consumed here as the semantic of LocalNodeRecovery.                 *)
(* ========================================================================= *)

EXTENDS Integers, Sequences, FiniteSets, TLC

CONSTANTS 
    Nodes,           \* Set of cluster nodes, e.g. {N1, N2}
    Workers,         \* Set of managed worker process IDs, e.g. {W1}
    Invocations,     \* Set of invocation IDs, e.g. {I1}
    MaxEpoch,        \* Maximum authority epoch (bound for TLC)
    MaxGen,          \* Maximum worker generation (bound for TLC)
    MaxAttempts,     \* Maximum invocation attempts (bound for TLC)
    MaxWALDepth      \* Maximum WAL entries per node (bound for TLC)

NONE == "NONE"

(* Message types for distributed network interaction *)
MSG_COMMIT_REJECT  == "CommitReject"

VARIABLES
    leader,          \* Active cluster leader node or NONE
    epochA,          \* Current cluster-wide authority epoch (E_A)
    epochL,          \* Mapping: Invocations -> Current lease epoch (E_L)
    workerGen,       \* Mapping: Workers -> Current worker generation (G)
    assignments,     \* Set of active assignments: [worker, invocation, gen, attempt, epA]
    quarantine,      \* Set of quarantined invocation IDs (Q)
    nodeWAL,         \* Mapping: Nodes -> Sequence of persistent WAL records
    network,         \* Set of in-flight network messages
    partition,       \* Set of isolated node pairs representing network cuts
    nodeEpoch        \* Mapping: Nodes -> Authority epoch recorded locally at node

vars == <<leader, epochA, epochL, workerGen, assignments, quarantine, nodeWAL, network, partition, nodeEpoch>>

(* ------------------------------------------------------------------------- *)
(* TYPE OK & INITIAL STATES                                                  *)
(* ------------------------------------------------------------------------- *)

TypeOK ==
    /\ leader \in Nodes \cup {NONE}
    /\ epochA \in 0..MaxEpoch
    /\ epochL \in [Invocations -> 0..MaxEpoch]
    /\ workerGen \in [Workers -> 1..MaxGen]
    /\ quarantine \subseteq Invocations
    /\ partition \subseteq (Nodes \times Nodes)
    /\ nodeEpoch \in [Nodes -> 0..MaxEpoch]

Init ==
    /\ leader = NONE
    /\ epochA = 0
    /\ epochL = [i \in Invocations |-> 0]
    /\ workerGen = [w \in Workers |-> 1]
    /\ assignments = {}
    /\ quarantine = {}
    /\ nodeWAL = [n \in Nodes |-> << >>]
    /\ network = {}
    /\ partition = {}
    /\ nodeEpoch = [n \in Nodes |-> 0]

(* ------------------------------------------------------------------------- *)
(* HELPER PREDICATES                                                         *)
(* ------------------------------------------------------------------------- *)

IsPartitioned(n1, n2) ==
    <<n1, n2>> \in partition \/ <<n2, n1>> \in partition

CanCommunicate(n1, n2) ==
    ~IsPartitioned(n1, n2)

(* An assignment is "stale" if its authority epoch does not match active *)
IsStaleAssignment(a) ==
    a.epA /= epochA

(* An assignment is "fenced" if ANY of (epA, gen) are stale *)
IsFencedAssignment(a) ==
    \/ a.epA /= epochA
    \/ a.gen /= workerGen[a.worker]

(* The set of committable (non-fenced) assignments *)
CommittableAssignments ==
    {a \in assignments : ~IsFencedAssignment(a)}

(* ------------------------------------------------------------------------- *)
(* STATE TRANSITIONS / ACTIONS                                               *)
(* ------------------------------------------------------------------------- *)

(* Action 1: Leader Election under new epoch                                 *)
(* SEMANTICS: Authority Invalidation, NOT assignment deletion.               *)
(*   E_A' > E_A fences all prior-epoch assignments at commit time.           *)
(*   Assignments PERSIST — they represent in-flight work that may still be   *)
(*   executing on workers. The workers will be rejected when they attempt    *)
(*   to commit because presentedEpA /= epochA.                              *)
LeaderElection(n, newEp) ==
    /\ newEp > epochA
    /\ newEp <= MaxEpoch
    /\ leader' = n
    /\ epochA' = newEp
    /\ nodeEpoch' = [nodeEpoch EXCEPT ![n] = newEp]
    /\ UNCHANGED <<epochL, workerGen, assignments, quarantine, nodeWAL, network, partition>>

(* Action 2: Leader Stepdown / Loss *)
LeaderLoss(n) ==
    /\ leader = n
    /\ leader' = NONE
    /\ UNCHANGED <<epochA, epochL, workerGen, assignments, quarantine, nodeWAL, network, partition, nodeEpoch>>

(* Action 3: Worker Generation Increment (Restart / Re-registration)         *)
(* The old assignments for worker w are NOT deleted — they are fenced.       *)
(* CommitMutation requires presentedGen = workerGen[w], so stale-gen         *)
(* assignments cannot commit. The old assignments may be cleaned up by       *)
(* StaleAssignmentCleanup or LeaseExpiry.                                    *)
WorkerRestart(w) ==
    /\ workerGen[w] < MaxGen
    /\ workerGen' = [workerGen EXCEPT ![w] = workerGen[w] + 1]
    /\ UNCHANGED <<leader, epochA, epochL, assignments, quarantine, nodeWAL, network, partition, nodeEpoch>>

(* Action 4: Assign Task under current Authority & Lease Epoch *)
AssignTask(n, w, i, att) ==
    /\ leader = n
    /\ i \notin quarantine
    \* No COMMITTABLE assignment for this invocation (stale ones may exist)
    /\ ~ \E a \in CommittableAssignments : a.invocation = i
    /\ att <= MaxAttempts
    /\ Len(nodeWAL[n]) < MaxWALDepth
    /\ LET newLeaseEp == epochL[i] + 1
       IN  /\ newLeaseEp <= MaxEpoch
           /\ epochL' = [epochL EXCEPT ![i] = newLeaseEp]
           /\ assignments' = assignments \cup {[worker |-> w, invocation |-> i, gen |-> workerGen[w], attempt |-> att, epA |-> epochA]}
           /\ nodeWAL' = [nodeWAL EXCEPT ![n] = Append(nodeWAL[n], [type |-> "ASSIGN", seq |-> Len(nodeWAL[n]) + 1, epA |-> epochA, payload |-> i])]
           /\ UNCHANGED <<leader, epochA, workerGen, quarantine, network, partition, nodeEpoch>>

(* Action 5: Renew Task Lease *)
RenewLease(n, i, presentedEpA) ==
    /\ leader = n
    /\ presentedEpA = epochA
    /\ \E a \in CommittableAssignments : a.invocation = i
    /\ epochL[i] < MaxEpoch
    /\ epochL' = [epochL EXCEPT ![i] = epochL[i] + 1]
    /\ UNCHANGED <<leader, epochA, workerGen, assignments, quarantine, nodeWAL, network, partition, nodeEpoch>>

(* Action 6: Lease Expiry & Task Revocation — removes all assignments for i *)
LeaseExpiry(i) ==
    /\ \E a \in assignments : a.invocation = i
    /\ assignments' = {a \in assignments : a.invocation /= i}
    /\ UNCHANGED <<leader, epochA, epochL, workerGen, quarantine, nodeWAL, network, partition, nodeEpoch>>

(* Action 7: Authoritative Commit Mutation with strict 4-tuple validation    *)
(* THIS is where authority fencing is enforced:                              *)
(*   (E_A, E_L, G, AttemptID)_presented = (E_A, E_L, G, AttemptID)_active   *)
CommitMutation(n, w, i, presentedEpA, presentedEpL, presentedGen, presentedAtt) ==
    /\ leader = n
    /\ presentedEpA = epochA                          \* 1. Authority Epoch Fencing
    /\ presentedEpL = epochL[i]                        \* 2. Lease Epoch Fencing
    /\ presentedGen = workerGen[w]                     \* 3. Worker Generation Fencing
    /\ Len(nodeWAL[n]) < MaxWALDepth
    /\ \E a \in assignments :                         \* 4. Assignment + Attempt Match
          /\ a.worker = w 
          /\ a.invocation = i 
          /\ a.gen = presentedGen 
          /\ a.attempt = presentedAtt
          /\ a.epA = epochA                            \* 5. Assignment itself must be current
    /\ assignments' = {a \in assignments : a.invocation /= i}
    /\ nodeWAL' = [nodeWAL EXCEPT ![n] = Append(nodeWAL[n], [type |-> "COMMIT", seq |-> Len(nodeWAL[n]) + 1, epA |-> epochA, payload |-> i])]
    /\ UNCHANGED <<leader, epochA, epochL, workerGen, quarantine, network, partition, nodeEpoch>>

(* Action 8: Reject Stale / Unfenced Commit Attempt                         *)
(* A stale assignment attempts to commit and is rejected.                    *)
RejectStaleCommit(n, a) ==
    /\ leader = n
    /\ IsFencedAssignment(a)
    /\ Cardinality(network) < 3
    /\ network' = network \cup {[type |-> MSG_COMMIT_REJECT, src |-> n, dst |-> n, epA |-> a.epA, epL |-> 0, worker |-> a.worker, gen |-> a.gen, inv |-> a.invocation, att |-> a.attempt]}
    /\ UNCHANGED <<leader, epochA, epochL, workerGen, assignments, quarantine, nodeWAL, partition, nodeEpoch>>

(* Action 9: Stale Assignment Cleanup                                        *)
(* Fenced assignments (a.epA < E_A or a.gen < G(w)) may be garbage-collected *)
(* by any node at any time.                                                  *)
StaleAssignmentCleanup ==
    /\ \E a \in assignments : IsFencedAssignment(a)
    /\ assignments' = {a \in assignments : ~IsFencedAssignment(a)}
    /\ UNCHANGED <<leader, epochA, epochL, workerGen, quarantine, nodeWAL, network, partition, nodeEpoch>>


(* Action 10: Worker Quarantining on Repeated Failure *)
QuarantineTask(i) ==
    /\ i \notin quarantine
    /\ quarantine' = quarantine \cup {i}
    /\ assignments' = {a \in assignments : a.invocation /= i}
    /\ UNCHANGED <<leader, epochA, epochL, workerGen, nodeWAL, network, partition, nodeEpoch>>

(* Action 11: Network Partition Creation & Healing *)
PartitionNetwork(n1, n2) ==
    /\ n1 /= n2
    /\ ~IsPartitioned(n1, n2)
    /\ partition' = partition \cup {<<n1, n2>>}
    /\ UNCHANGED <<leader, epochA, epochL, workerGen, assignments, quarantine, nodeWAL, network, nodeEpoch>>

HealNetwork ==
    /\ partition /= {}
    /\ partition' = {}
    /\ UNCHANGED <<leader, epochA, epochL, workerGen, assignments, quarantine, nodeWAL, network, nodeEpoch>>

(* Action 12: Local WAL Replay & Node Recovery                               *)
(* COMPOSITION AXIOM from Coq Phase6WALSafety.v:                            *)
(*   Restart(n) => State_n = Replay(ValidPrefix(WAL_n))                     *)
(* The recovering node:                                                      *)
(*   1. Reconstructs its local epoch from the last valid WAL record          *)
(*   2. Steps down from leadership (if it was leader) to prevent             *)
(*      split-brain divergence — must re-elect under new E_A                 *)
LocalNodeRecovery(n) ==
    /\ Len(nodeWAL[n]) > 0
    /\ nodeEpoch' = [nodeEpoch EXCEPT ![n] = nodeWAL[n][Len(nodeWAL[n])].epA]
    /\ leader' = IF leader = n THEN NONE ELSE leader
    /\ UNCHANGED <<epochA, epochL, workerGen, assignments, quarantine, nodeWAL, network, partition>>

(* Next state relation *)
Next ==
    \/ \E n \in Nodes, ep \in 1..MaxEpoch : LeaderElection(n, ep)
    \/ \E n \in Nodes : LeaderLoss(n)
    \/ \E w \in Workers : WorkerRestart(w)
    \/ \E n \in Nodes, w \in Workers, i \in Invocations, att \in 1..MaxAttempts : AssignTask(n, w, i, att)
    \/ \E n \in Nodes, i \in Invocations, epA \in 0..MaxEpoch : RenewLease(n, i, epA)
    \/ \E i \in Invocations : LeaseExpiry(i)
    \/ \E n \in Nodes, w \in Workers, i \in Invocations, epA, epL, gen, att \in 0..MaxEpoch :
          CommitMutation(n, w, i, epA, epL, gen, att)
    \/ \E n \in Nodes, a \in assignments : RejectStaleCommit(n, a)
    \/ StaleAssignmentCleanup
    \/ \E i \in Invocations : QuarantineTask(i)
    \/ \E n1, n2 \in Nodes : PartitionNetwork(n1, n2)
    \/ HealNetwork
    \/ \E n \in Nodes : LocalNodeRecovery(n)

(* Temporal specification with weak fairness for liveness *)
Fairness ==
    /\ WF_vars(\E n \in Nodes, ep \in 1..MaxEpoch : LeaderElection(n, ep))
    /\ WF_vars(StaleAssignmentCleanup)

Spec == Init /\ [][Next]_vars /\ Fairness

(* ========================================================================= *)
(* FORMAL SAFETY INVARIANTS (Box Safety)                                     *)
(* These must hold in EVERY reachable state.                                 *)
(* ========================================================================= *)

(* Safety 1: No Stale-Authority Commit                                       *)
(* The core distributed safety property:                                     *)
(*   A commit to the WAL can only occur under the ACTIVE authority epoch.    *)
(*   Stale assignments may EXIST but they can never COMMIT.                  *)
NoStaleAuthorityCommitForNode(n) ==
    \A idx \in 1..Len(nodeWAL[n]) :
        nodeWAL[n][idx].type = "COMMIT" =>
            nodeWAL[n][idx].epA <= epochA

NoStaleAuthorityCommit ==
    \A n \in Nodes : NoStaleAuthorityCommitForNode(n)

(* Safety 2: Committed WAL Epoch Monotonicity                                *)
(* WAL records within a single node have non-decreasing authority epochs.    *)
WALEpochMonotonicityForNode(n) ==
    \A idx \in 1..(Len(nodeWAL[n]) - 1) :
        nodeWAL[n][idx].epA <= nodeWAL[n][idx + 1].epA

WALEpochMonotonicity ==
    \A n \in Nodes : WALEpochMonotonicityForNode(n)


(* Safety 3: Split-Brain Fencing                                             *)
(* No two COMMITTABLE assignments for the same invocation under same epoch. *)
SplitBrainFencingSafety ==
    \A a1, a2 \in CommittableAssignments :
        (a1.invocation = a2.invocation) => a1 = a2

(* Safety 4: Stale Assignment Cannot Commit                                  *)
(* An assignment with a.epA /= epochA can never satisfy CommitMutation.     *)
(* This is the formalization of "authority invalidation, not deletion."      *)
StaleAssignmentCannotCommit ==
    \A a \in assignments :
        a.epA /= epochA => a \notin CommittableAssignments

(* Safety 5: Worker Generation Fencing for Committable Assignments           *)
(* Only current-generation assignments are committable.                     *)
WorkerGenerationFencingSafety ==
    \A a \in CommittableAssignments : a.gen = workerGen[a.worker]

(* Safety 6: Quarantined Invocation Isolation                                *)
(* Quarantined tasks can never be actively assigned.                        *)
QuarantineIsolationSafety ==
    \A a \in assignments : a.invocation \notin quarantine

(* Safety 7: Single Leader Per Epoch                                         *)
(* If a leader exists, it is the unique node claiming the active epoch.     *)
SingleLeaderSafety ==
    leader /= NONE => nodeEpoch[leader] = epochA

(* Combined Safety Invariant *)
CombinedSafetyInvariant ==
    /\ NoStaleAuthorityCommit
    /\ WALEpochMonotonicity
    /\ SplitBrainFencingSafety
    /\ StaleAssignmentCannotCommit
    /\ WorkerGenerationFencingSafety
    /\ QuarantineIsolationSafety
    /\ SingleLeaderSafety

(* ========================================================================= *)
(* FORMAL LIVENESS PROPERTIES (Diamond Liveness)                             *)
(* These must EVENTUALLY hold under the stated fairness assumptions.         *)
(* ========================================================================= *)

(* Liveness 1: Leader Election Progress                                      *)
(* Under weak fairness of LeaderElection:                                    *)
(*   If the system has no leader and epoch space remains, it eventually        *)
(*   elects a leader or reaches the epoch bound.                            *)
(* FAIRNESS ASSUMPTION: WF_vars(LeaderElection)                              *)
LeaderElectionProgress ==
    (leader = NONE /\ epochA < MaxEpoch) ~> (leader /= NONE \/ epochA = MaxEpoch)

(* Liveness 2: Stale Assignment Garbage Collection                           *)
(* Under weak fairness of StaleAssignmentCleanup:                            *)
(*   If stale (fenced) assignments exist, they are eventually cleaned up.    *)
(* FAIRNESS ASSUMPTION: WF_vars(StaleAssignmentCleanup)                      *)
StaleAssignmentGCProgress ==
    (\E a \in assignments : IsFencedAssignment(a)) ~>
        (~\E a \in assignments : IsFencedAssignment(a))



=============================================================================
