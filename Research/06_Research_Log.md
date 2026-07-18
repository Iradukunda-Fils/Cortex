# 06: Research Log

Cumulative evidence log tracking composition evaluations, discoveries, and strategic pivots.

---

## Entry: 2026.07.18-A — Semantic Framework Established

**Milestone:** Established the Generalized Semantic Transition Relation ($\Sigma; \Lambda \vdash I \Longrightarrow e$) and the safety properties catalog (P1–P4). Demoted P2 to an environmental assumption. Multi-system validation expanded to four structural domains to eliminate narrow domain bias.

---

## Entry: 2026.07.18-B — CC-01 Complete

**Composition Evaluated:** CC-01 (Whole-System Provenance + Capability Security)

**Verdict:** Partially Covered.

**Key Finding:** Kernel provenance (CamFlow at LSM boundary) captures syscalls and OS events but is structurally blind to user-space operational artifacts ($\mathcal{A}$). When memory is mutated after derivation of plan ($\mathcal{A}$) but before enactment, the capability layer passes the call (P1/P2 SUCCESS) but cannot establish whether the target action is a valid semantic consequence of delegation constraints ($\Sigma \models \text{Preserves}(\Lambda, e)$ FAILED).

---

## Entry: 2026.07.18-C — CC-04 Complete

**Composition Evaluated:** CC-04 (Capability Security + Program Logics / Dependently Typed Execution)

**Verdict:** Partially Covered.

**Key Finding:** Refinement types and monadic effects verify static pathway semantics. When dynamic workflows are processed by a user-space interpreter embedded inside the typed engine, the host compiler's soundness proofs verify the interpreter wrapper but cannot verify the operational trace occurring within the interpreter's virtual space.

**Critical Formalization (Verified Interpreter Objection Rebuttal):** A formally verified interpreter proves $\text{Interpreter}(Program, In) \equiv \text{Semantics}(Program, In)$ which guarantees execution fidelity. It does **not** prove that the derived operational artifact's ($\mathcal{A}$) strategy choices are a valid semantic consequence of the original delegation constraints. This is a structural absence in the proof, not an implementation bug.

---

## Entry: 2026.07.18-D — Strategic Pivot: 5-Part Survey Blueprint Activated

**Status:** Meta-Design Finalized. Structural Operational Semantics Parameterized on "Operational Artifacts" ($\mathcal{A}$) via the Generalized Semantic Transition System ($\xrightarrow{\text{derive}}$ and $\xrightarrow{\text{enact}}$) to avoid forcing distinct system states into a privileged vocabulary. All downstream composition analyses remain strictly frozen.

**Decision:** The research program commits exclusively to producing a 5-part core semantic survey blueprint. The new survey file list is established:
1.  [07_Correspondence_Survey.md](07_Correspondence_Survey.md) (Formal Definitions of Existing Relations)
2.  [08_Evaluation_Relations.md](08_Evaluation_Relations.md) (Computation & Planning paradigms)
3.  [09_Delegation_Semantics.md](09_Delegation_Semantics.md) (Authority boundaries)
4.  [10_Preservation_Relations.md](10_Preservation_Relations.md) (Preservation, Simulation, & Logical Relations)
5.  [11_Semantic_Objects.md](11_Semantic_Objects.md) (Mathematical categories of objects)

**Progress:** 
- Finalized taxonomy expansion to include Algebraic & Rewriting Frameworks (#20) in `04_Literature_Taxonomy.md` and decoupled Secure Compilation (#19) toward behavioral preservation.
- Partitioned semantic domains from primary semantic objects in `11_Semantic_Objects.md` to prevent category errors (e.g., capability protection graphs vs. logic judgments).
- Restructured `10_Preservation_Relations.md` across a 4-dimensional matrix and integrated Simulation and Logical Relations, establishing a formal posture on the inadequacy of standard logical relations for decoupled, untyped intermediary authority constraints.
- Expanded `09_Delegation_Semantics.md` to map Capability Architectures, Language-Based Capabilities, Resource & Structural Logics, and Authorization Logics.

**Next Step:** The meta-design phase is officially closed. The program proceeds directly to executing the formal literature deep dives for Documents 07 through 11, determining if the target relational hyperproperty $\Sigma \models \text{Preserves}(\Lambda, e)$ truly remains unmapped in the entirety of the CS literature.
