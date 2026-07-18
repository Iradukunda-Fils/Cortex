# 06: Research Log

Cumulative evidence log tracking composition evaluations, discoveries, and strategic pivots.

---

## Entry: 2026.07.18-A — Semantic Framework Established

**Milestone:** Established the Evaluation Relation ($\Sigma; \Lambda \vdash I \Longrightarrow e$) and the safety properties catalog (P1–P4). Demoted P2 to an environmental assumption. Multi-system validation expanded to four structural domains to eliminate narrow domain bias.

---

## Entry: 2026.07.18-B — CC-01 Complete

**Composition Evaluated:** CC-01 (Whole-System Provenance + Capability Security)

**Verdict:** Partially Covered.

**Key Finding:** Kernel provenance (CamFlow at LSM boundary) captures syscalls and OS events but is structurally blind to user-space operational artifacts ($\mathcal{A}$). When memory is mutated after plan construction but before interface dispatch, the capability layer passes the call (P1/P2 SUCCESS) but cannot establish whether the target action is a valid semantic consequence of delegation constraints ($\Sigma \models \text{Preserves}(\Lambda, e)$ FAILED).

---

## Entry: 2026.07.18-C — CC-04 Complete

**Composition Evaluated:** CC-04 (Capability Security + Program Logics / Dependently Typed Execution)

**Verdict:** Partially Covered.

**Key Finding:** Refinement types and monadic effects verify static pathway semantics. When dynamic workflows are processed by a user-space interpreter embedded inside the typed engine, the host compiler's soundness proofs verify the interpreter wrapper but cannot verify the operational trace occurring within the interpreter's virtual space.

**Critical Formalization (Verified Interpreter Objection Rebuttal):** A formally verified interpreter proves $\text{Interpreter}(Program, In) \equiv \text{Semantics}(Program, In)$ which guarantees execution fidelity. It does **not** prove that the generated program's strategy choices are a valid semantic consequence of the original delegation constraints. The type system evaluates the interpreter's wrapper; it cannot natively bind the generated program's dynamic strategy to the external authority envelope. This is a structural absence, not an implementation bug.

---

## Entry: 2026.07.18-D — Strategic Pivot: 5-Part Survey Blueprint Activated

**Status:** Meta-Design Finalized. Structural Operational Semantics Parameterized on "Operational Artifacts" ($\mathcal{A}$) to avoid forcing distinct system states into a privileged vocabulary. All downstream composition analyses remain strictly frozen.

**Decision:** The research program commits exclusively to producing a 5-part core semantic survey blueprint to systematically map logical consequence, evaluated semantics, delegation paradigms, security preservation theorems, and mathematical categories of objects. The new survey file list is established:
1.  [07_Correspondence_Survey.md](07_Correspondence_Survey.md) (Formal Definitions of Existing Relations)
2.  [08_Evaluation_Relations.md](08_Evaluation_Relations.md) (Computation & Planning paradigms)
3.  [09_Delegation_Semantics.md](09_Delegation_Semantics.md) (Authority boundaries)
4.  [10_Preservation_Relations.md](10_Preservation_Relations.md) (Expanded taxonomy of type, refinement, and secure compilation theorems)
5.  [11_Semantic_Objects.md](11_Semantic_Objects.md) (NEW - Mathematical categories of objects)

**Progress:** 
- Successfully finalized the taxonomy expansion to include Institutional Semantics (#20) in `04_Literature_Taxonomy.md` and reframed Secure Compilation (#19) around behavioral preservation and security hyperproperties.
- Drafted and locked `11_Semantic_Objects.md` containing the mathematical category mappings.
- Refactored `10_Preservation_Relations.md` into a highly structured survey utilizing the four-dimensional taxonomy.
- Updated terminology across all active and locked documents to center around standard PL vocabulary, operational artifacts, and the rephrased hypothesis.

**Next Step:** Evaluate if our target predicate $\Sigma \models \text{Preserves}(\Lambda, e)$ can be formally classified as a novel subclass of Robust Property Preservation (from secure compilation) or if it presents a completely isolated, irreducible semantic relationship.
