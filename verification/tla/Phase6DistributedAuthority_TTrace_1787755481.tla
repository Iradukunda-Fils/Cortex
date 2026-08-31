---- MODULE Phase6DistributedAuthority_TTrace_1787755481 ----
EXTENDS Phase6DistributedAuthority, Sequences, TLCExt, Phase6DistributedAuthority_TEConstants, Toolbox, Naturals, TLC

_expression ==
    LET Phase6DistributedAuthority_TEExpression == INSTANCE Phase6DistributedAuthority_TEExpression
    IN Phase6DistributedAuthority_TEExpression!expression
----

_trace ==
    LET Phase6DistributedAuthority_TETrace == INSTANCE Phase6DistributedAuthority_TETrace
    IN Phase6DistributedAuthority_TETrace!trace
----

_prop ==
    ~<>[](
        leader = ("NONE")
        /\
        workerGen = ((W1 :> 2))
        /\
        partition = ({})
        /\
        assignments = ({[epA |-> 2, gen |-> 2, worker |-> W1, invocation |-> I1, attempt |-> 1], [epA |-> 3, gen |-> 2, worker |-> W1, invocation |-> I1, attempt |-> 2]})
        /\
        nodeEpoch = ((N1 :> 0 @@ N2 :> 3))
        /\
        epochL = ((I1 :> 2))
        /\
        nodeWAL = ((N1 :> <<>> @@ N2 :> <<[epA |-> 2, type |-> "ASSIGN", seq |-> 1, payload |-> I1], [epA |-> 3, type |-> "ASSIGN", seq |-> 2, payload |-> I1]>>))
        /\
        quarantine = ({})
        /\
        network = ({})
        /\
        epochA = (3)
    )
----

_init ==
    /\ nodeEpoch = _TETrace[1].nodeEpoch
    /\ leader = _TETrace[1].leader
    /\ workerGen = _TETrace[1].workerGen
    /\ partition = _TETrace[1].partition
    /\ network = _TETrace[1].network
    /\ epochA = _TETrace[1].epochA
    /\ assignments = _TETrace[1].assignments
    /\ epochL = _TETrace[1].epochL
    /\ quarantine = _TETrace[1].quarantine
    /\ nodeWAL = _TETrace[1].nodeWAL
----

_next ==
    /\ \E i,j \in DOMAIN _TETrace:
        /\ \/ /\ j = i + 1
              /\ i = TLCGet("level")
        /\ nodeEpoch  = _TETrace[i].nodeEpoch
        /\ nodeEpoch' = _TETrace[j].nodeEpoch
        /\ leader  = _TETrace[i].leader
        /\ leader' = _TETrace[j].leader
        /\ workerGen  = _TETrace[i].workerGen
        /\ workerGen' = _TETrace[j].workerGen
        /\ partition  = _TETrace[i].partition
        /\ partition' = _TETrace[j].partition
        /\ network  = _TETrace[i].network
        /\ network' = _TETrace[j].network
        /\ epochA  = _TETrace[i].epochA
        /\ epochA' = _TETrace[j].epochA
        /\ assignments  = _TETrace[i].assignments
        /\ assignments' = _TETrace[j].assignments
        /\ epochL  = _TETrace[i].epochL
        /\ epochL' = _TETrace[j].epochL
        /\ quarantine  = _TETrace[i].quarantine
        /\ quarantine' = _TETrace[j].quarantine
        /\ nodeWAL  = _TETrace[i].nodeWAL
        /\ nodeWAL' = _TETrace[j].nodeWAL

\* Uncomment the ASSUME below to write the states of the error trace
\* to the given file in Json format. Note that you can pass any tuple
\* to `JsonSerialize`. For example, a sub-sequence of _TETrace.
    \* ASSUME
    \*     LET J == INSTANCE Json
    \*         IN J!JsonSerialize("Phase6DistributedAuthority_TTrace_1787755481.json", _TETrace)

=============================================================================

 Note that you can extract this module `Phase6DistributedAuthority_TEExpression`
  to a dedicated file to reuse `expression` (the module in the 
  dedicated `Phase6DistributedAuthority_TEExpression.tla` file takes precedence 
  over the module `Phase6DistributedAuthority_TEExpression` below).

---- MODULE Phase6DistributedAuthority_TEExpression ----
EXTENDS Phase6DistributedAuthority, Sequences, TLCExt, Phase6DistributedAuthority_TEConstants, Toolbox, Naturals, TLC

expression == 
    [
        \* To hide variables of the `Phase6DistributedAuthority` spec from the error trace,
        \* remove the variables below.  The trace will be written in the order
        \* of the fields of this record.
        nodeEpoch |-> nodeEpoch
        ,leader |-> leader
        ,workerGen |-> workerGen
        ,partition |-> partition
        ,network |-> network
        ,epochA |-> epochA
        ,assignments |-> assignments
        ,epochL |-> epochL
        ,quarantine |-> quarantine
        ,nodeWAL |-> nodeWAL
        
        \* Put additional constant-, state-, and action-level expressions here:
        \* ,_stateNumber |-> _TEPosition
        \* ,_nodeEpochUnchanged |-> nodeEpoch = nodeEpoch'
        
        \* Format the `nodeEpoch` variable as Json value.
        \* ,_nodeEpochJson |->
        \*     LET J == INSTANCE Json
        \*     IN J!ToJson(nodeEpoch)
        
        \* Lastly, you may build expressions over arbitrary sets of states by
        \* leveraging the _TETrace operator.  For example, this is how to
        \* count the number of times a spec variable changed up to the current
        \* state in the trace.
        \* ,_nodeEpochModCount |->
        \*     LET F[s \in DOMAIN _TETrace] ==
        \*         IF s = 1 THEN 0
        \*         ELSE IF _TETrace[s].nodeEpoch # _TETrace[s-1].nodeEpoch
        \*             THEN 1 + F[s-1] ELSE F[s-1]
        \*     IN F[_TEPosition - 1]
    ]

=============================================================================



Parsing and semantic processing can take forever if the trace below is long.
 In this case, it is advised to uncomment the module below to deserialize the
 trace from a generated binary file.

\*
\*---- MODULE Phase6DistributedAuthority_TETrace ----
\*EXTENDS Phase6DistributedAuthority, IOUtils, Phase6DistributedAuthority_TEConstants, TLC
\*
\*trace == IODeserialize("Phase6DistributedAuthority_TTrace_1787755481.bin", TRUE)
\*
\*=============================================================================
\*

---- MODULE Phase6DistributedAuthority_TETrace ----
EXTENDS Phase6DistributedAuthority, Phase6DistributedAuthority_TEConstants, TLC

trace == 
    <<
    ([leader |-> "NONE",workerGen |-> (W1 :> 1),partition |-> {},assignments |-> {},nodeEpoch |-> (N1 :> 0 @@ N2 :> 0),epochL |-> (I1 :> 0),nodeWAL |-> (N1 :> <<>> @@ N2 :> <<>>),quarantine |-> {},network |-> {},epochA |-> 0]),
    ([leader |-> "NONE",workerGen |-> (W1 :> 2),partition |-> {},assignments |-> {},nodeEpoch |-> (N1 :> 0 @@ N2 :> 0),epochL |-> (I1 :> 0),nodeWAL |-> (N1 :> <<>> @@ N2 :> <<>>),quarantine |-> {},network |-> {},epochA |-> 0]),
    ([leader |-> N2,workerGen |-> (W1 :> 2),partition |-> {},assignments |-> {},nodeEpoch |-> (N1 :> 0 @@ N2 :> 2),epochL |-> (I1 :> 0),nodeWAL |-> (N1 :> <<>> @@ N2 :> <<>>),quarantine |-> {},network |-> {},epochA |-> 2]),
    ([leader |-> N2,workerGen |-> (W1 :> 2),partition |-> {},assignments |-> {[epA |-> 2, gen |-> 2, worker |-> W1, invocation |-> I1, attempt |-> 1]},nodeEpoch |-> (N1 :> 0 @@ N2 :> 2),epochL |-> (I1 :> 1),nodeWAL |-> (N1 :> <<>> @@ N2 :> <<[epA |-> 2, type |-> "ASSIGN", seq |-> 1, payload |-> I1]>>),quarantine |-> {},network |-> {},epochA |-> 2]),
    ([leader |-> N2,workerGen |-> (W1 :> 2),partition |-> {},assignments |-> {[epA |-> 2, gen |-> 2, worker |-> W1, invocation |-> I1, attempt |-> 1]},nodeEpoch |-> (N1 :> 0 @@ N2 :> 3),epochL |-> (I1 :> 1),nodeWAL |-> (N1 :> <<>> @@ N2 :> <<[epA |-> 2, type |-> "ASSIGN", seq |-> 1, payload |-> I1]>>),quarantine |-> {},network |-> {},epochA |-> 3]),
    ([leader |-> N2,workerGen |-> (W1 :> 2),partition |-> {},assignments |-> {[epA |-> 2, gen |-> 2, worker |-> W1, invocation |-> I1, attempt |-> 1], [epA |-> 3, gen |-> 2, worker |-> W1, invocation |-> I1, attempt |-> 2]},nodeEpoch |-> (N1 :> 0 @@ N2 :> 3),epochL |-> (I1 :> 2),nodeWAL |-> (N1 :> <<>> @@ N2 :> <<[epA |-> 2, type |-> "ASSIGN", seq |-> 1, payload |-> I1], [epA |-> 3, type |-> "ASSIGN", seq |-> 2, payload |-> I1]>>),quarantine |-> {},network |-> {},epochA |-> 3]),
    ([leader |-> "NONE",workerGen |-> (W1 :> 2),partition |-> {},assignments |-> {[epA |-> 2, gen |-> 2, worker |-> W1, invocation |-> I1, attempt |-> 1], [epA |-> 3, gen |-> 2, worker |-> W1, invocation |-> I1, attempt |-> 2]},nodeEpoch |-> (N1 :> 0 @@ N2 :> 3),epochL |-> (I1 :> 2),nodeWAL |-> (N1 :> <<>> @@ N2 :> <<[epA |-> 2, type |-> "ASSIGN", seq |-> 1, payload |-> I1], [epA |-> 3, type |-> "ASSIGN", seq |-> 2, payload |-> I1]>>),quarantine |-> {},network |-> {},epochA |-> 3])
    >>
----


=============================================================================

---- MODULE Phase6DistributedAuthority_TEConstants ----
EXTENDS Phase6DistributedAuthority

CONSTANTS N1, N2, W1, I1

=============================================================================

---- CONFIG Phase6DistributedAuthority_TTrace_1787755481 ----
CONSTANTS
    Nodes = { N1 , N2 }
    Workers = { W1 }
    Invocations = { I1 }
    MaxEpoch = 3
    MaxGen = 2
    MaxAttempts = 2
    MaxWALDepth = 3
    N1 = N1
    N2 = N2
    W1 = W1
    I1 = I1

PROPERTY
    _prop

CHECK_DEADLOCK
    \* CHECK_DEADLOCK off because of PROPERTY or INVARIANT above.
    FALSE

INIT
    _init

NEXT
    _next

CONSTANT
    _TETrace <- _trace

ALIAS
    _expression
=============================================================================
\* Generated on Wed Aug 26 15:45:59 WAT 2026