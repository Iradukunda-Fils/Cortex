# 02: Domain Model
**Status:** LOCKED  

## Purpose
Define the system boundaries, threat model, safety properties catalog, and multi-system adversarial scenarios that bound the research program.

## Dependencies
*   [01_Methodology.md](01_Methodology.md)

---

## 1. The Primary Research Hypothesis

Can existing semantic frameworks express and verify the correspondence between delegated authority and dynamically synthesized irreversible effects under an adversarial execution model?

*   **Null Hypothesis ($H_0$):** For every safety property in this catalog, there exists a composition of existing computer science frameworks that satisfies it under the stated threat model without introducing new semantic primitives.
*   **Alternative Hypothesis ($H_1$):** No composition of existing frameworks satisfies all safety properties simultaneously under the stated threat model, exposing an irreducible semantic gap.

**Conditional Outcome:**
*   If the composition analysis succeeds: The program concludes that existing CS frameworks are sufficient. No new semantic layer is required.
*   If the composition analysis fails: The analysis exposes an irreducible semantic gap. Only then does a candidate specification materialize to formalize those newly discovered semantics.

---

## 2. System Boundaries

The domain bounds the intersection of three distinct operational states:

*   **Delegated Authority:** The downstream propagation of programmatic capability boundaries from a root principal to a dynamic executor.
*   **Runtime Decision Synthesis:** The process by which an execution path or structural operation is generated non-deterministically at runtime by an evaluation engine. Formally: an Evaluation Relation (I→T→e) mapping an input stream (I) through an execution trace (T) to a target action (e).
*   **Irreversible External Effects:** State modifications crossing the external system frontier that cannot be rolled back without structural side effects or economic/operational compromises.

---

## 3. Multi-System Adversarial Scenarios

To strip away narrow domain bias and prove this is a fundamental systems challenge, evaluations are applied across four distinct structural domains:

| System Domain | Concrete Execution / Target Parameter Context |
| --- | --- |
| **Distributed DBMS Query Optimizer** | A JIT-compiled SQL execution plan generating dynamic index mutations or high-cost data deletes. |
| **Infrastructure Orchestration** | A Kubernetes Autoscaler calculating scheduling migrations that trigger irreversible node teardowns. |
| **Autonomous Systems (Robotics)** | A robotic controller translating lidar telemetry paths into irreversible physical hardware actions. |
| **Autonomous Medical Execution** | A diagnostic model converting clinical telemetry streams into automated physical drug administration. |

---

## 4. Safety Properties Catalog

Every candidate composition in `05_Composition_Analysis.md` must be rigidly cross-examined against this catalog. No new properties may be introduced post-hoc. Properties are orthogonal and non-overlapping.

| ID | Safety Property | Definitive Operational Meaning | Historical Coverage |
| --- | --- | --- | --- |
| **P1** | **Authority Soundness** | Bounded authority must be delegable and attenuable across downstream context shifts such that a principal cannot execute or delegate permissions beyond its initial envelope. | Object-Capabilities, Macaroons, Biscuit, SPKI |
| **P2** | **Execution Integrity** | The byte-level parameter state of an executed action must remain structurally unaltered between the generation boundary and the interface enforcement perimeter under the stated threat model. | Enclave memory isolation, Single-copy buffers, Verified compilation |
| **P3** | **Causal Correspondence** | The execution framework must be capable of demonstrating that the dynamically synthesized target action is a valid semantic consequence of the active delegation constraints. | **No known complete solution** |
| **P4** | **Independent Verifiability** | An external, post-facto verifier must be capable of establishing the validity of P3 without trusting the integrity of the execution runtime after the action has occurred. | **No known complete solution** |

> **Note:** P2 (Execution Integrity) is demoted from a research objective to a **baseline Environmental Assumption** managed by established systems techniques (Rust memory safety, hardware enclaves, authenticated channels). The active research focus is on P3 and P4.
