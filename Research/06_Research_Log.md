# 06: Research Log

Cumulative evidence log tracking composition evaluations, discoveries, and strategic pivots.

---

## Entry: 2026.07.18-A — Semantic Framework Established

**Milestone:** Established the Evaluation Relation (I→T→e) and the condensed four-property Safety Properties Catalog (P1–P4). Demoted P2 to an environmental assumption. Multi-system validation expanded to four structural domains to eliminate narrow domain bias.

---

## Entry: 2026.07.18-B — CC-01 Complete

**Composition Evaluated:** CC-01 (Whole-System Provenance + Capability Security)

**Verdict:** Partially Covered.

**Key Finding:** Kernel provenance (CamFlow at LSM boundary) captures syscalls and OS events but is structurally blind to user-space program evaluation traces (T). When memory is mutated after trace synthesis but before interface dispatch, the capability layer passes the call (P1/P2 SUCCESS) but cannot establish whether the target action is a valid semantic consequence of delegation constraints (P3/P4 FAILED).

| Property | Result |
| --- | --- |
| P1 (Authority Soundness) | SUCCESS |
| P2 (Execution Integrity) | SUCCESS |
| P3 (Semantic Consequence Preservation) | FAILED |
| P4 (Independent Verifiability) | FAILED |

---

## Entry: 2026.07.18-C — CC-04 Complete

**Composition Evaluated:** CC-04 (Capability Security + Program Logics / Dependently Typed Execution)

**Verdict:** Partially Covered.

**Key Finding:** Refinement types and monadic effects verify static pathway semantics. When dynamic, user-submitted workflows are processed by a user-space interpreter embedded inside the typed engine, the host compiler's soundness proofs verify the interpreter module but cannot verify the synthesis trajectory occurring within the interpreter's virtual space.

**Critical Formalization (Verified Interpreter Objection Rebuttal):** A formally verified interpreter proves $\text{Interpreter}(Program, Input) \equiv \text{Semantics}(Program, Input)$. This guarantees execution fidelity. It does **not** prove that the synthesized program's strategy choices are a valid semantic consequence of the original delegation constraints. The type system evaluates the interpreter's wrapper; it cannot natively bind the synthesized program's dynamic strategy to the external authority envelope. This is a structural absence, not an implementation bug.

| Property | Result |
| --- | --- |
| P1 (Authority Soundness) | SUCCESS |
| P2 (Execution Integrity) | SUCCESS |
| P3 (Semantic Consequence Preservation) | PARTIAL (native compiled; fails for nested interpreted) |
| P4 (Independent Verifiability) | FAILED |

---

## Cross-Composition Pattern Analysis (CC-01 → CC-04)

| Composition | Enforcement Layer | P3 | P4 | Core Gap |
| --- | --- | --- | --- | --- |
| CC-01 (Provenance + O-Caps) | Kernel-level Telemetry | FAILED | FAILED | Evaluation trace (T) is opaque to OS boundary |
| CC-04 (O-Caps + Program Logics) | Type-level Refinements | PARTIAL | FAILED | Nested interpreters bypass compile-time proof scope |

**Emerging Pattern:** CC-01 exposes the OS-to-application boundary gap. CC-04 exposes the compiler-to-dynamic-interpreter boundary gap. Both show that once execution traces are dynamically synthesized by non-fixed evaluation relations, neither kernel-level observation nor compile-time type systems can verify semantic consequence preservation across the delegation boundary.

---

## Entry: 2026.07.18-D — Strategic Pivot: Research Question 0 Activated

**Status:** Meta-Design Complete. Systematic Evaluation Log Initialized.

**Decision:** All downstream composition analyses (CC-05 and beyond) are frozen. The program executes an exhaustive, formal baseline mapping of what "correspondence" means across computer science history before attempting any further system-level compositions.

**Rationale:** With CC-01 and CC-04 both isolating structural absences in proven framework areas, we must formally verify that the proof obligation we seek to express in P3/P4 is not simply a renamed variant of a correspondence already fully proven by an existing discipline. This is the mandatory prerequisite under the Semantic Inversion Stopping Rule.

**Research Question 0 Statement:** For each major discipline that claims to express a "correspondence" between program behavior and a specification, identify: (1) the specific correspondence relation verified, (2) its formal mathematical expression, and (3) the precise formal boundary at which it fails to cover $H_0$.

**Survey Finding (Injected into 01_Methodology.md):** After mapping 8 distinct semantic correspondence relations across all surveyed disciplines (Hoare Logic, Refinement Calculus, IFC, Capability Systems, Provenance, Temporal Logic, Separation Logic, Proof-Carrying Code), no surveyed discipline defines, expresses, or enforces a correspondence relation that:

> Preserves a proof obligation across a delegation boundary when the program $c$ being executed is itself the output of a runtime synthesis process whose evaluation relation is not fixed before execution.

This is not a naming ambiguity — it is a **structural absence** in the landscape of known semantic correspondences.

---

## Next Target: Deep Semantic Baseline Analysis

**Focus:** Identifying the precise mathematical intersection where existing correspondences — specifically Program Logics (16) vs. Information Flow Control (12) — break down when forced to carry a delegated proof obligation through an unfixed runtime synthesis process.

**Methodology:** Systematic edge-case documentation in this log before any further system-level composition is attempted.

**Key Questions to Resolve:**
1.  Can Hoare Logic be extended to parameterize $c$ as a runtime-generated term while preserving the triple's proof obligation?
2.  Can IFC label propagation be extended to track delegation constraints (not merely data integrity levels) through a synthesis trace?
3.  Is there an existing formalism (e.g., contextual equivalence, logical relations, bisimulation) that naturally spans the delegation-boundary correspondence gap?
