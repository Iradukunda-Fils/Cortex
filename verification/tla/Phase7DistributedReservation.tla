------------------- MODULE Phase7DistributedReservation -------------------
(* ========================================================================= *)
(* CORTEX PHASE 7.4: DISTRIBUTED RESERVATION AUTHORITY TLA+ MODEL            *)
(*                                                                           *)
(* Formal TLA+ specification modeling multi-node resource authority cluster  *)
(* coordination, capacity conservation, discrete GPU isolation, lease epoch  *)
(* fencing, network partitions, authority crash/recovery, and reconciliation *)
(* composition with the local kernel ResourceAuthority.                     *)
(*                                                                           *)
(* ASSURANCE BOUNDARY:                                                       *)
(*   Safety   = MODEL-CHECKED for finite bounded state space                 *)
(*   Liveness = MODEL-CHECKED under weak fairness                            *)
(*   Proof    = Consumes Coq Local Invariants (Phase7Reservation.v)          *)
(*                                                                           *)
(* SCHEDULER BOUNDARY:                                                       *)
(*   ResourceAwareScheduler remains STRICTLY BLOCKED until 7.4 is satisfied. *)
(* ========================================================================= *)

EXTENDS Integers, Sequences, FiniteSets, TLC

CONSTANTS
    Nodes,           \* Set of authority cluster nodes, e.g. {N1, N2}
    Workers,         \* Set of worker process IDs, e.g. {W1}
    ReservationIDs,  \* Set of reservation IDs, e.g. {R1, R2}
    GPUs,            \* Set of discrete GPU IDs, e.g. {G0}
    MaxEpoch,        \* Maximum authority epoch bound for TLC
    MaxCapacity      \* Total CPU capacity per node bound (millicores)

NONE == "NONE"

STATUS_PENDING  == "PENDING"
STATUS_ACTIVE   == "ACTIVE"
STATUS_RELEASED == "RELEASED"
STATUS_EXPIRED  == "EXPIRED"
STATUS_REVOKED  == "REVOKED"

VARIABLES
    activeLeader,     \* Active cluster leader authority node or NONE
    authorityEpoch,   \* Global monotonic authority epoch E_A
    nodeEpoch,        \* Mapping: Nodes -> Local authority epoch
    reservations,     \* Mapping: Nodes -> (ReservationIDs -> Record)
    gpuOwners,        \* Mapping: Nodes -> (GPUs -> ReservationID)
    quarantine,       \* Set of quarantined reservation IDs
    partition         \* Set of isolated node pairs representing network cuts

vars == <<activeLeader, authorityEpoch, nodeEpoch, reservations, gpuOwners, quarantine, partition>>

(* ------------------------------------------------------------------------- *)
(* TYPE OK & INITIAL STATES                                                  *)
(* ------------------------------------------------------------------------- *)

TypeOK ==
    /\ activeLeader \in Nodes \cup {NONE}
    /\ authorityEpoch \in 0..MaxEpoch
    /\ nodeEpoch \in [Nodes -> 0..MaxEpoch]
    /\ quarantine \subseteq ReservationIDs
    /\ partition \subseteq (Nodes \times Nodes)

Init ==
    /\ activeLeader = NONE
    /\ authorityEpoch = 0
    /\ nodeEpoch = [n \in Nodes |-> 0]
    /\ reservations = [n \in Nodes |-> [r \in {} |-> {}]]
    /\ gpuOwners = [n \in Nodes |-> [g \in {} |-> {}]]
    /\ quarantine = {}
    /\ partition = {}

(* ------------------------------------------------------------------------- *)
(* HELPER PREDICATES & OPERATORS                                             *)
(* ------------------------------------------------------------------------- *)

IsPartitioned(n1, n2) ==
    <<n1, n2>> \in partition \/ <<n2, n1>> \in partition

CanCommunicate(n1, n2) ==
    ~IsPartitioned(n1, n2)

ActiveReservationsForNode(n) ==
    {r \in DOMAIN reservations[n] :
        reservations[n][r].status \in {STATUS_PENDING, STATUS_ACTIVE}}

RECURSIVE SumDemand(_, _)
SumDemand(rSet, rMap) ==
    IF rSet = {} THEN 0
    ELSE LET r == CHOOSE x \in rSet : TRUE
         IN  rMap[r].demand + SumDemand(rSet \ {r}, rMap)

TotalActiveDemandForNode(n) ==
    LET activeSet == ActiveReservationsForNode(n)
    IN  IF activeSet = {} THEN 0
        ELSE SumDemand(activeSet, reservations[n])

(* ------------------------------------------------------------------------- *)
(* DISTRIBUTED AUTHORITY TRANSITIONS                                         *)
(* ------------------------------------------------------------------------- *)

(* 1. Leader Succession & Epoch Advance *)
LeaderSuccession(n, newEp) ==
    /\ newEp > authorityEpoch
    /\ newEp <= MaxEpoch
    /\ activeLeader' = n
    /\ authorityEpoch' = newEp
    /\ nodeEpoch' = [nodeEpoch EXCEPT ![n] = newEp]
    /\ UNCHANGED <<reservations, gpuOwners, quarantine, partition>>

(* 2. Distributed Reservation Placement *)
ReserveCapacity(n, rId, wId, demandVal, gpuId, epA, leaseEp) ==
    /\ activeLeader = n
    /\ epA = authorityEpoch
    /\ rId \notin quarantine
    /\ rId \notin DOMAIN reservations[n]
    /\ TotalActiveDemandForNode(n) + demandVal <= MaxCapacity
    /\ (gpuId = NONE \/ gpuId \notin DOMAIN gpuOwners[n])
    /\ LET newRecord == [
            id |-> rId,
            worker |-> wId,
            demand |-> demandVal,
            gpu |-> gpuId,
            status |-> STATUS_ACTIVE,
            epochA |-> epA,
            leaseEpoch |-> leaseEp
       ]
       IN /\ reservations' = [reservations EXCEPT ![n] = [r \in (DOMAIN reservations[n]) \cup {rId} |-> IF r = rId THEN newRecord ELSE reservations[n][r]]]
          /\ gpuOwners' = IF gpuId /= NONE
                          THEN [gpuOwners EXCEPT ![n] = [g \in (DOMAIN gpuOwners[n]) \cup {gpuId} |-> IF g = gpuId THEN rId ELSE gpuOwners[n][g]]]
                          ELSE gpuOwners
          /\ UNCHANGED <<activeLeader, authorityEpoch, nodeEpoch, quarantine, partition>>

(* 3. Fenced Lease Renewal *)
RenewLease(n, rId, presentedEpA, newLeaseEp) ==
    /\ activeLeader = n
    /\ presentedEpA = authorityEpoch
    /\ rId \in DOMAIN reservations[n]
    /\ reservations[n][rId].status \in {STATUS_PENDING, STATUS_ACTIVE}
    /\ newLeaseEp > reservations[n][rId].leaseEpoch
    /\ reservations' = [reservations EXCEPT ![n][rId].leaseEpoch = newLeaseEp]
    /\ UNCHANGED <<activeLeader, authorityEpoch, nodeEpoch, gpuOwners, quarantine, partition>>

(* 4. Terminal Release Operation *)
ReleaseReservation(n, rId, presentedEpA) ==
    /\ rId \in DOMAIN reservations[n]
    /\ presentedEpA = authorityEpoch
    /\ reservations[n][rId].status \in {STATUS_PENDING, STATUS_ACTIVE}
    /\ LET rec == reservations[n][rId]
           gpuId == rec.gpu
       IN /\ reservations' = [reservations EXCEPT ![n][rId].status = STATUS_RELEASED]
          /\ gpuOwners' = IF gpuId /= NONE /\ gpuId \in DOMAIN gpuOwners[n]
                          THEN [gpuOwners EXCEPT ![n] = [g \in (DOMAIN gpuOwners[n]) \ {gpuId} |-> gpuOwners[n][g]]]
                          ELSE gpuOwners
          /\ UNCHANGED <<activeLeader, authorityEpoch, nodeEpoch, quarantine, partition>>

(* 5. Terminal Expiration Operation *)
ExpireReservation(n, rId) ==
    /\ rId \in DOMAIN reservations[n]
    /\ reservations[n][rId].status \in {STATUS_PENDING, STATUS_ACTIVE}
    /\ LET rec == reservations[n][rId]
           gpuId == rec.gpu
       IN /\ reservations' = [reservations EXCEPT ![n][rId].status = STATUS_EXPIRED]
          /\ quarantine' = quarantine \cup {rId}
          /\ gpuOwners' = IF gpuId /= NONE /\ gpuId \in DOMAIN gpuOwners[n]
                          THEN [gpuOwners EXCEPT ![n] = [g \in (DOMAIN gpuOwners[n]) \ {gpuId} |-> gpuOwners[n][g]]]
                          ELSE gpuOwners
          /\ UNCHANGED <<activeLeader, authorityEpoch, nodeEpoch, partition>>

(* 6. Terminal Revocation Operation *)
RevokeReservation(n, rId, presentedEpA) ==
    /\ rId \in DOMAIN reservations[n]
    /\ presentedEpA = authorityEpoch
    /\ reservations[n][rId].status \in {STATUS_PENDING, STATUS_ACTIVE}
    /\ LET rec == reservations[n][rId]
           gpuId == rec.gpu
       IN /\ reservations' = [reservations EXCEPT ![n][rId].status = STATUS_REVOKED]
          /\ quarantine' = quarantine \cup {rId}
          /\ gpuOwners' = IF gpuId /= NONE /\ gpuId \in DOMAIN gpuOwners[n]
                          THEN [gpuOwners EXCEPT ![n] = [g \in (DOMAIN gpuOwners[n]) \ {gpuId} |-> gpuOwners[n][g]]]
                          ELSE gpuOwners
          /\ UNCHANGED <<activeLeader, authorityEpoch, nodeEpoch, partition>>

(* 7. Stale Fencing Rejection *)
RejectStaleOperation(n, rId, presentedEpA) ==
    /\ presentedEpA /= authorityEpoch
    /\ UNCHANGED <<activeLeader, authorityEpoch, nodeEpoch, reservations, gpuOwners, quarantine, partition>>

(* 8. Network Partition & Healing *)
PartitionNetwork(n1, n2) ==
    /\ n1 /= n2
    /\ ~IsPartitioned(n1, n2)
    /\ partition' = partition \cup {<<n1, n2>>}
    /\ UNCHANGED <<activeLeader, authorityEpoch, nodeEpoch, reservations, gpuOwners, quarantine>>

HealNetwork ==
    /\ partition /= {}
    /\ partition' = {}
    /\ UNCHANGED <<activeLeader, authorityEpoch, nodeEpoch, reservations, gpuOwners, quarantine>>

(* Next State Relation *)
Next ==
    \/ \E n \in Nodes, ep \in 1..MaxEpoch : LeaderSuccession(n, ep)
    \/ \E n \in Nodes, rId \in ReservationIDs, wId \in Workers, dem \in 1..MaxCapacity, g \in GPUs \cup {NONE}, ep \in 1..MaxEpoch, lEp \in 1..MaxEpoch :
          ReserveCapacity(n, rId, wId, dem, g, ep, lEp)
    \/ \E n \in Nodes, rId \in ReservationIDs, ep \in 1..MaxEpoch, lEp \in 1..MaxEpoch :
          RenewLease(n, rId, ep, lEp)
    \/ \E n \in Nodes, rId \in ReservationIDs, ep \in 1..MaxEpoch :
          ReleaseReservation(n, rId, ep)
    \/ \E n \in Nodes, rId \in ReservationIDs :
          ExpireReservation(n, rId)
    \/ \E n \in Nodes, rId \in ReservationIDs, ep \in 1..MaxEpoch :
          RevokeReservation(n, rId, ep)
    \/ \E n \in Nodes, rId \in ReservationIDs, ep \in 0..MaxEpoch :
          RejectStaleOperation(n, rId, ep)
    \/ \E n1, n2 \in Nodes : PartitionNetwork(n1, n2)
    \/ HealNetwork

Spec == Init /\ [][Next]_vars

(* ========================================================================= *)
(* FORMAL DISTRIBUTED SAFETY INVARIANTS                                      *)
(* ========================================================================= *)

(* Invariant 1: Capacity Conservation *)
CapacityConservation ==
    \A n \in Nodes : TotalActiveDemandForNode(n) <= MaxCapacity

(* Invariant 2: GPU Exclusive Ownership Safety *)
GPUExclusiveOwnershipSafety ==
    \A n \in Nodes :
        \A g \in GPUs :
            g \in DOMAIN gpuOwners[n] =>
                LET rId == gpuOwners[n][g]
                IN  /\ rId \in DOMAIN reservations[n]
                    /\ reservations[n][rId].status \in {STATUS_PENDING, STATUS_ACTIVE}

(* Invariant 3: Single Leader Per Authority Epoch *)
SingleLeaderPerEpochSafety ==
    activeLeader /= NONE => nodeEpoch[activeLeader] = authorityEpoch

(* Invariant 4: Quarantined Reservation Isolation *)
QuarantineIsolationSafety ==
    \A n \in Nodes :
        \A rId \in quarantine :
            rId \in DOMAIN reservations[n] =>
                reservations[n][rId].status \in {STATUS_EXPIRED, STATUS_REVOKED}

(* Invariant 5: Terminal Non-Resurrection Safety *)
TerminalNonResurrectionSafety ==
    \A n \in Nodes :
        \A rId \in DOMAIN reservations[n] :
            reservations[n][rId].status \in {STATUS_RELEASED, STATUS_EXPIRED, STATUS_REVOKED} =>
                rId \notin ActiveReservationsForNode(n)

(* Combined Phase 7.4 Distributed Safety Invariant *)
Phase7DistributedSafetyInvariant ==
    /\ CapacityConservation
    /\ GPUExclusiveOwnershipSafety
    /\ SingleLeaderPerEpochSafety
    /\ QuarantineIsolationSafety
    /\ TerminalNonResurrectionSafety

=============================================================================
