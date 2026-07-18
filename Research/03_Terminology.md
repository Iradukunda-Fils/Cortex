# 03: Terminology
**Status:** LOCKED  

## Purpose
Ground core domain concepts in reproducible, abstract computer science primitives. Definitions serve as the universal mathematical language for every subsequent composition audit.

## Dependencies
*   [02_Domain_Model.md](02_Domain_Model.md)

## Rules
1.  Every definition must be self-contained.
2.  No circular references.
3.  No synonyms. Rejected alternatives are explicitly listed.
4.  No polysemy.
5.  Formal notation is grounded in established CS primitives (lattice theory, type theory, process calculi).

---

## Foundational Primitives

### Authority Space ($A$)
*   **Definition:** A bounded lattice of permissible system state transformations delegated from a root principal.
*   **Grounding:** Lattice theory; capability security (Dennis & Van Horn).
*   **Rejected Synonyms:** Permission set, Access scope.

### Delegation Context ($\Lambda$)
*   **Definition:** A principal's cryptographic statement mapping a subset of authority to a target execution context, satisfying the relation $\Lambda \sqsubseteq A$. Delegation is monotonically attenuating.
*   **Grounding:** SPKI/SDSI (RFC 2693), Macaroons, Biscuit.
*   **Rejected Synonyms:** Authorization grant, Token scope.

### Delegation Lineage
*   **Definition:** The complete, ordered chain of delegation acts from the root authority grant to the currently active delegation context. Each link carries its own attenuation constraints.
*   **Rejected Synonyms:** Authorization chain, Trust path.

### Target Action Tuple ($e$)
*   **Definition:** The concrete execution parameter vector crossing the system boundary to induce an irreversible effect: $e = \langle \text{op}, \text{args} \rangle \in E_{\text{irreversible}}$.
*   **Grounding:** Operating systems theory (system call interface), formal specifications (action semantics).
*   **Rejected Synonyms:** Effect, Operation, Command.

### Causal Witness Vector ($\mathcal{W}$)
*   **Definition:** The set of cryptographic hashes of all external state inputs consumed to compute the derivation trace elements. Enables deterministic reconstruction of the trace graph by an independent auditor.
*   **Grounding:** Cryptographic commitment schemes, Merkle tree constructions.
*   **Rejected Synonyms:** Input log, Evidence record.

### Runtime Derivation (or Evaluation Derivation)
*   **Definition:** The dynamic compilation, interpretation, or translation process that maps a stream of non-deterministic input parameters ($I$) to a tuple representing its operational derivation: $T = \langle \mathcal{D}, \tau, \mathcal{P} \rangle$.
*   **Grounding:** Compiler construction (JIT compilation traces), interpreter theory, structural operational semantics (SOS).
*   **Rejected Synonyms:** Runtime Synthesis, Dynamic Parameter Synthesis, Autonomous Planning.

### Derivation Tree ($\mathcal{D}$)
*   **Definition:** The formal, meta-logical proof object composed of a tree of inference rules demonstrating that the execution engine accurately followed its language or operational semantics to translate input stream $I$.
*   **Rejected Synonyms:** Evaluation proof, Syntax tree.

### Operational Trace ($\tau$)
*   **Definition:** The linear or branching sequential history of intermediate micro-state transitions executed by the underlying abstract or concrete machine during evaluation.
*   **Rejected Synonyms:** State log, Microtrace.

### Execution Plan ($\mathcal{P}$)
*   **Definition:** The intermediate structural artifact emitted by the derivation process which is subsequently consumed by an enforcement engine to induce real-world state shifts.
*   **Rejected Synonyms:** Execution schedule, Command block.

### Decision Derivation Node ($\Delta$)
*   **Definition:** A structurally bounded execution state tuple representing a complete runtime derivation event: $\Delta = \langle e, \Lambda, \langle \mathcal{D}, \tau, \mathcal{P} \rangle, \mathcal{W} \rangle$.
*   **Components:**
    *   $e$: The generated Target Action Tuple.
    *   $\Lambda$: The Delegation Context (coarse permission perimeter).
    *   $\langle \mathcal{D}, \tau, \mathcal{P} \rangle$: The Runtime Derivation artifacts.
    *   $\mathcal{W}$: The Causal Witness Vector (cryptographic input commitments).
*   **Rejected Synonyms:** Decision record, Execution event, Synthesis node.

### Observation Model ($\mathcal{M}_{\text{obs}}$)
*   **Definition:** The formal architectural perimeter defining what a tracking or logging mechanism can inspect, intercept, and record about execution state (e.g., kernel LSM hooks vs. user-space application logs).
*   **Rejected Synonyms:** Monitoring scope, Telemetry boundary.

### Verification Perimeter ($\mathcal{V}$)
*   **Definition:** The enforcement boundary at which the complete decision derivation node $\Delta$ is evaluated to determine whether the consequence relation holds before permitting execution of the irreversible effect.
*   **Formal Role:** Evaluates whether $\Sigma \models \text{Preserves}(\Lambda, e)$ using the artifacts in $\Delta$.
*   **Rejected Synonyms:** Enforcement point, Policy decision point.

### Authorized Consequence Relation ($\vdash$)
*   **Definition:** An inference relation over a bounded policy language representing a strict mathematical proof that the emitted target action tuple $e$ falls within the valid refinement space defined by the delegation context $\Lambda$, as demonstrated through the derivation trace structures.
*   **Grounding:** Type theory (judgment forms), formal logic (inference rules).
*   **Rejected Synonyms:** Authorization check, Access control decision, Policy evaluation.

---

## Deprecated Terms

| Deprecated Term | Replaced By | Rationale |
| --- | --- | --- |
| Dynamic Parameter Synthesis | Runtime Derivation | More precise; aligns with operational evaluation definitions. |
| Runtime Decision Synthesis | Runtime Derivation | More precise; aligns with operational evaluation definitions. |
| Synthesis Trajectory Matrix | Runtime Derivation tuple $\langle \mathcal{D}, \tau, \mathcal{P} \rangle$ | Formally partitioned to prevent semantics confusion. |
| Independently Verifiable Causality Proof | Causal Witness Vector ($\mathcal{W}$) + Derivation Trace | Decomposed into formal components. |
| Effect | Target Action Tuple ($e$) | Formally grounded with structural definition. |
| Agent Host | *(not replaced)* | Implementation-specific. |
