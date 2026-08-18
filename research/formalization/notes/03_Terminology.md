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
*   **Definition:** A semantic object whose interpretation constrains the admissible externally observable effects of an execution. Formally, it represents a principal's cryptographic statement mapping a subset of authority, satisfying the relation $\Lambda \sqsubseteq A$.
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
*   **Definition:** The set of cryptographic hashes of all external state inputs consumed to compute the operational artifact. Enables deterministic reconstruction of the execution path by an independent auditor.
*   **Grounding:** Cryptographic commitment schemes, Merkle tree constructions.
*   **Rejected Synonyms:** Input log, Evidence record.

### Operational Artifact ($\mathcal{A}$)
*   **Definition:** Anything produced by an execution procedure that is subsequently interpreted to determine externally observable behavior.
*   **Subclasses:**
    *   **Evaluation Derivation**: AST to value mappings in operational semantics.
    *   **Query Plan**: Relational operators tree in DB query systems.
    *   **Workflow Plan**: Distributed task dependency DAG in choreographies.
    *   **Scheduling Plan**: Resource and host allocations in schedulers.
    *   **Proof Object**: Typed $\lambda$-calculus term or logical proof witness.
    *   **Execution Graph**: Transition system state graph.
    *   **Optimization Trace**: Compiler optimization records.
*   **Rejected Synonyms:** Runtime Synthesis, Runtime Derivation, Synthesis Trajectory.

### Derivation Procedure ($\xrightarrow{\text{derive}}$)
*   **Definition:** An abstract computational procedure (such as evaluation, interpretation, planning, scheduling, compilation, optimization, or elaboration) that processes inputs ($I$) inside the global state ($\Sigma$) and under the initial delegation context ($\Lambda$) to yield an intermediate Operational Artifact ($\mathcal{A}$).
*   **Rejected Synonyms:** Compilation pass, Translation pass.

### Enforcement Procedure ($\xrightarrow{\text{enact}}$)
*   **Definition:** An abstract machine execution phase (such as execution, interpretation, scheduling, optimization, dispatching, or hardware pipelining) that consumes an operational artifact ($\mathcal{A}$) to yield a terminal effect ($e$). Under the generalized rule, it retains the semantic capability to continuously consult or attenuate against the delegation context ($\Lambda$) at any point during execution.
*   **Rejected Synonyms:** Execution pass, Dispatcher loop.

### Decision Node ($\Delta$)
*   **Definition:** A structurally bounded execution state tuple representing a complete execution decision event: $\Delta = \langle e, \Lambda, \mathcal{A}, \mathcal{W} \rangle$.
*   **Rejected Synonyms:** Decision record, Execution event, Synthesis node.

### Observation Model ($\mathcal{M}_{\text{obs}}$)
*   **Definition:** The formal architectural perimeter defining what a tracking or logging mechanism can inspect, intercept, and record about execution state (e.g., kernel LSM hooks vs. user-space application logs).
*   **Rejected Synonyms:** Monitoring scope, Telemetry boundary.

### Verification Perimeter ($\mathcal{V}$)
*   **Definition:** The enforcement boundary at which the complete decision node $\Delta$ is evaluated to determine whether the consequence relation holds before permitting execution of the irreversible effect.
*   **Formal Role:** Evaluates whether $\Sigma \models \text{Preserves}(\Lambda, e)$ using the artifacts in $\Delta$.
*   **Rejected Synonyms:** Enforcement point, Policy decision point.

### Authorized Consequence Relation ($\vdash$)
*   **Definition:** An inference relation over a bounded policy language representing a strict mathematical proof that the emitted target action tuple $e$ falls within the valid refinement space defined by the delegation context $\Lambda$, as demonstrated through the operational metadata.
*   **Grounding:** Type theory (judgment forms), formal logic (inference rules).
*   **Rejected Synonyms:** Authorization check, Access control decision, Policy evaluation.

---

## Deprecated Terms

| Deprecated Term | Replaced By | Rationale |
| --- | --- | --- |
| Dynamic Parameter Synthesis | Operational Artifact ($\mathcal{A}$) | Standardizes semantic representations across system domains. |
| Runtime Decision Synthesis | Operational Artifact ($\mathcal{A}$) | Standardizes semantic representations across system domains. |
| Runtime Derivation | Operational Artifact ($\mathcal{A}$) | Standardizes semantic representations across system domains. |
| Synthesis Trajectory Matrix | Operational Artifact ($\mathcal{A}$) | Standardizes semantic representations across system domains. |
| Independently Verifiable Causality Proof | Causal Witness Vector ($\mathcal{W}$) + Operational Artifact ($\mathcal{A}$) | Decomposed into formal components. |
| Effect | Target Action Tuple ($e$) | Formally grounded with structural definition. |
| Agent Host | *(not replaced)* | Implementation-specific. |
