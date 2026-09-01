# Gate F: Formal-to-Concrete Refinement Specification

**Author:** Iradukunda Fils <iradukundafils1@gmail.com>  
**Role:** Systems Architect & Hardware/Software Co-Designer  
**Status:** NORMATIVE ARCHITECTURAL SPECIFICATION (PHASE 14 GATE F REFINEMENT)  
**Date:** August 16, 2026  

---

## 1. Executive Summary & Refinement Purpose

The Cortex platform has achieved **104/104 implementation certification checks** across the Profile A Linux sandbox supervisor, Gateway TCB, and independent untrusted verifier. Empirical testing demonstrates that the system executes correctly under all tested adversarial vectors.

However, empirical testing proves only that tested execution paths behave correctly under tested scenarios; it does not prove the absence of unconsidered execution paths. **Gate F (Formal Refinement)** establishes the mathematical bridge between the physical implementation ($C$) and the Coq formal specification ($M$).

Rather than forcing a rigid 1-to-1 abstraction function $\alpha(C) = M$, Gate F is formally modeled as a **Forward Simulation Relation $R \subseteq C \times M$ with Stuttering Steps**:

```text
                  FORWARD SIMULATION WITH STUTTERING STEPS

      Concrete State (C) ───────────────────────► Concrete State (C')
             │                                           │
             │ Simulation Relation                       │ Simulation Relation
             │ R(C, M)                                   │ R(C', M')
             ▼                                           ▼
       Formal State (M) ───[ spec_step / ID ]────────► Formal State (M')
```

### 1.1 Stuttering vs. Refinement Steps
* **Internal Operations (Stuttering Steps)**: Concrete operations $C \xrightarrow{\text{impl}} C'$ (IPC socket framing, JSON-RPC parsing, signature verification, `ExecutionToken` allocation) alter implementation state without changing abstract semantic state:
  $$R(C, M) \land C \xrightarrow{\text{impl}} C' \implies R(C', M)$$
* **Semantic Operations (Refinement Steps)**: When an effect actuation or capability attenuation completes, the concrete step corresponds to a non-trivial Coq step:
  $$R(C, M) \land C \xrightarrow{\text{actuate}} C' \implies \exists M', M \xrightarrow{\text{spec}} M' \land R(C', M')$$

---

## 2. Five Formal Trust & Assumption Boundaries

To prevent unbounded formal verification scope creep while preserving mathematical rigor, five explicit boundaries are declared:

| Verification Boundary | Formal Scope & Invariant Definition | Responsibility |
| :--- | :--- | :--- |
| **`[FORMALLY PROVEN]`** | Pure mechanized Coq proofs of state transitions, monotonic authority attenuation ($P1$), intent parity ($P2$), witness lineage ($P3$), and verifier soundness ($P4$). | Coq (`Soundness.v`, `World.v`) |
| **`[REFINEMENT-VERIFIED]`** | Provable simulation relation $R(C, M)$ mapping concrete runtime/RTL states to abstract Coq types. | Refinement Specifications & Coq Mapping |
| **`[CRYPTOGRAPHIC ASSUMPTION]`** | Standard cryptographic hardness assumptions accepted as foundational primitives (SHA-256 collision resistance, Ed25519 signature validity, UUID uniqueness). | Axiomatic Substrate Baseline |
| **`[PLATFORM ASSUMPTION]`** | Linux kernel isolation invariants (Namespaces, Seccomp-BPF, Landlock LSM) behave according to documented OS security semantics. | Kernel Security Baseline |
| **`[HARDWARE ASSUMPTION]`** | Physical synthesis and Verilator simulation preserve the verified Verilog RTL semantics of `cortex_stcr_pipeline.sv`. | Silicon / FPGA Target |

---

## 3. Disambiguating Physical Mechanics from Abstract Properties

### 3.1 Operational State vs. Semantic Mediation Invariant ($P0$)
`gateway_active = true` is an operational runtime flag; it is not equivalent to complete mediation. Complete Mediation ($P0$) is defined as a formal invariant over all reachable effect paths:
$$\text{MediationInvariant}(S) \triangleq \forall e \in \text{ReachableEffects}(S), \text{MediatedByGateway}(e)$$
The Profile A supervisor, namespace boundaries, and Seccomp filters serve as concrete evidence demonstrating that this invariant holds over $C$.

### 3.2 Disaggregated Hardware Traps (F3)
Concrete hardware failures in `cortex_stcr_pipeline.sv` map to distinct formal failure classes rather than a generic trap:

$$\begin{array}{rcl}
\text{STCR.valid} = 0 &\iff& \text{Formal Capability Invalid} \\
\text{STCR.scope} \land \text{Req} = 0 &\iff& \text{Formal Scope Violation} \\
\text{reg\_hec} > \text{Epoch}_{\max} &\iff& \text{Formal Temporal / Epoch Expiration}
\end{array}$$

### 3.3 Hardware Width Independence (Gate L1)
The Hardware Epoch Counter (HEC) semantic invariant is monotonic non-wrapping progression, independent of register bit-width:
$$\forall t_1 < t_2, \quad \text{HEC}(t_1) \le \text{HEC}(t_2) \quad \land \quad \left( \text{Overflow}(t_2) \implies \text{Trap}(t_2) \right)$$
A 64-bit width is one physical implementation option ensuring overflow impossibility within operational runtime lifetimes.

---

## 4. Four Gate F Refinement Sub-Gates

```text
                                    GATE F SUB-GATES
                                           │
   ┌───────────────────┬───────────────────┴───────────────────┬───────────────────┐
   ▼                   ▼                                       ▼                   ▼
Sub-Gate F1         Sub-Gate F2 (includes L2)               Sub-Gate F3 (includes L1) Sub-Gate F4
State Repr.         Capability Attenuation                  Transition & Invocation   Evidence & Witness
$\alpha_{\text{State}} / R_{\text{State}}$ $\alpha_{\text{Cap}} / R_{\text{Cap}}$ $\alpha_{\text{Exec}} / R_{\text{Exec}}$ $\alpha_{\text{Witness}} / R_{\text{Witness}}$
```

### 4.1 Sub-Gate F1: State Representation Refinement ($\alpha_{\text{State}}$ / $R_{\text{State}}$)
* **Component-wise Abstraction Map**:
  $$\alpha_{\text{State}}(C) \triangleq \left\langle \text{Authority} \leftarrow C.\text{stcr\_bank}, \text{Epoch} \leftarrow C.\text{reg\_hec}, \text{Mediation} \leftarrow C.\text{profile\_a\_active} \right\rangle$$
* **Proof Obligation F1.1**: $\forall C, \text{WellFormed}_{\text{impl}}(C) \implies \text{WellFormed}_{\text{spec}}(\alpha_{\text{State}}(C))$.

### 4.2 Sub-Gate F2: Capability & Attenuation Refinement ($\alpha_{\text{Cap}}$ / $R_{\text{Cap}}$) — *Unifies Gate L2*
* **Attenuation Proof Obligation F2.1**: Prove that concrete `restrict_cap` operations map directly to formal capability attenuation ($P1$):
  $$\text{ConcreteRestrict}(P, \text{constraints}, C) \implies \text{Scope}(\alpha(C)) \subseteq \text{Scope}(\alpha(P)) \land \text{Epoch}(\alpha(C)) \le \text{Epoch}(\alpha(P))$$
* **Hardware Gate L2 Integration (F2.2)**: Formally audit RTL Opcode `0x02` (`grant_cap`) in `cortex_stcr_pipeline.sv` to prove that derived capabilities cannot widen bitmask bounds beyond the parent STCR descriptor.

### 4.3 Sub-Gate F3: Transition & Invocation Refinement ($\alpha_{\text{Exec}}$ / $R_{\text{Exec}}$) — *Unifies Gate L1*
* **Forward Simulation Obligation F3.1**: Prove that processing a valid `SignedIntent` through the Gateway preserves simulation relation $R(C', M')$ relative to abstract `e_invoke`:
  $$R(C, M) \land C \xrightarrow{\text{valid\_intent}} C' \implies \exists M', M \xrightarrow{e\_invoke} M' \land R(C', M')$$
* **Hardware Gate L1 Integration (F3.2)**: Prove that HEC overflow or invalid STCR descriptors trigger hardware traps mapping directly to formal stale invocation semantics (`step_m_invoke_stale`, $\text{Result} = 0$).

### 4.4 Sub-Gate F4: Evidence & Witness Refinement ($\alpha_{\text{Witness}}$ / $R_{\text{Witness}}$)
* **Two-Stage Refinement Obligation**:
  $$\text{VerifiedWitness}(E) \implies \text{ConcreteEffectProvenance}(E) \implies \text{FormalEffectProvenance}(\alpha(E))$$
* **Crash Recovery Mapping**: Prove that a post-crash `RecoveryEvent` mapped to `VERIFIED-INDETERMINATE` maintains formal cryptographic witness chain validity while marking effect actuation outcome as unresolved.

---

## 5. Tactical Proof Development Order

```text
  ┌────────────────────────────────────────────────────────┐
  │ F1.1: State Correspondence & Well-Formedness           │
  │ Prove α(C) yields a structurally sound Coq World       │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ F2.1: Attenuation Correspondence (restrict_cap)        │
  │ Prove concrete attenuation preserves P1 Monotonicity   │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ F2.2: Capability Generation Audit (grant_cap / L2)     │
  │ Prove opcode 0x02 cannot derive expanded authority     │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ F3.1: Valid Invocation Simulation (e_invoke)           │
  │ Forward simulation for valid Intent -> Effect execution │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ F3.2: Stale Trap & Epoch Simulation (L1)               │
  │ Simulation for invalid STCR / HEC overflow traps       │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ F4: Evidence, Witness, & Recovery Refinement           │
  │ Map CommitEvent and Witness logs to formal provenance  │
  └────────────────────────────────────────────────────────┘
```
