# 13: Runtime Assurance
**Status:** LOCKED

## Purpose
Decouple Runtime Verification and dynamic monitoring from pure preservation theories. Establish a dedicated framework to evaluate execution assurance mechanisms operating concurrently with active execution traces.

## Dependencies
*   [02_Domain_Model.md](02_Domain_Model.md)
*   [12_Threat_Model.md](12_Threat_Model.md)

---

## 1. The Core Taxonomy Restructuring

We restructure the conceptual taxonomy into three non-overlapping pillars representing distinct phases of formal architecture:

```text
                              [ CORE TAXONOMY ]
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
[ Semantic Foundations ]       [ Authority Models ]         [ Execution Assurance ]
 ├── Operational Semantics      ├── Capabilities             ├── Runtime Verification
 ├── Program Logics             ├── Authorization Logics     ├── Whole-System Provenance
 ├── Static Analysis            └── Delegation Systems       └── Proof-Carrying Computation
 └── Secure Compilation
```

---

## 2. Execution Assurance Mechanisms

This document maps the disciplines focused directly on **Execution Assurance**:

### 2.1 Runtime Verification
*   **Focus:** Monitoring execution traces against formal specifications or temporal logic targets (LTL/MTL) during active execution.
*   **Architectures:** Enforcement monitors, shield synthesis, online trace compliance.

### 2.2 Whole-System Provenance
*   **Focus:** Interception of interactions (syscalls, file, network) at the kernel level to construct complete, append-only causal histories.
*   **Architectures:** CamFlow, PASS, SPADE.

### 2.3 Proof-Carrying Computation
*   **Focus:** Appending machine-checkable validation certificates to structural computational outputs to be verified downstream.
*   **Architectures:** Certified compilers, logic frameworks (Coq/Lean proof terms), cryptographic commitments.

---

## 3. Position Relative to the Working Hypothesis

While Execution Assurance mechanisms are highly capable of isolating and tracking execution steps ($\tau$), their fundamental limitation relative to $H_{\text{prop}}$ is that they assume the assurance specification is either statically pre-compiled or bounded to OS-level interception points. They lack the semantic context to continuously derive the boundaries of an intermediate Operational Artifact ($\mathcal{A}$) dynamically from a high-level external delegation context ($\Lambda$).
