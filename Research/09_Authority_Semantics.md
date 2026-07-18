# 09: Authority Semantics
**Status:** LOCKED

## 1. Purpose and Scope
This document surveys how authority, resource allocations, and operational permissions are formally represented, mutated, and validated across programming languages, software security architectures, and mathematical logics. Following our established structural dependency chain, this module builds directly upon the structural ontologies defined in `11_Semantic_Objects.md` and the environmental parameterization established in `12_Threat_Model.md`.

Rather than adopting a singular framework-specific abstraction at the outset, this module conducts a literature-first investigation into the diverse mathematical structures developed by different research communities to reason about authority. We analyze these structures across four orthogonal semantic axes: representation models, evolution mechanics, validation strategies, and preserved invariants. This rigorous deconstruction ensures that any downstream synthesis in `07_Correspondence_Survey.md` emerges naturally from a crosswalk of existing formalisms rather than an unproven assumption.

## 2. Structural Taxonomy of Authority Semantics
To categorize the extensive literature objectively, we organize the surveyed frameworks into a unified, non-overlapping semantic matrix based on their formal operational roles:

```text
                      [ AUTHORITY SEMANTICS ]
                                 │
     ┌───────────────────┬───────┴───────────┬───────────────────┐
     ▼                   ▼                   ▼                   ▼
[ Representation ]  [ Evolution ]      [ Validation ]      [ Preservation ]
 ├── Capability      ├── Creation       ├── Static Typings   ├── Confinement
 ├── Principal       ├── Delegation     ├── Dynamic Proofs   ├── Least Privilege
 ├── Permission      ├── Transfer       └── Hybrid Checkers  ├── Ownership Safety
 ├── Ownership       ├── Attenuation                         └── Soundness
 ├── Resource        ├── Borrowing
 ├── Security Label  ├── Revocation
 └── Effect/Cap      └── Consumption
```

## 3. Mathematical Representations of Authority (Question 1)
Different computing traditions inhabit distinct semantic domains to capture what an execution entity is authorized to perform.

> **Definitional Caveat:**
> Different traditions represent different aspects of authority, including invocation rights, ownership, confidentiality constraints, resource availability, or proof obligations. These notions overlap significantly but are not mathematically interchangeable. We systematically avoid flattening these distinctions, tracking the precise aspect of control each domain isolates.

We identify seven primary representation models within the literature:

### 3.1 Object-Capabilities (O-Caps)
*   **Mathematical Domain:** Directed reference graphs over protection domains, where vertices represent objects or actors and edges represent unforgeable reference handles.
*   **Landmark Literature Baselines:** Dennis and Van Horn (1966), Miller, Griep, and Van Cutsem (2003, Robust Composition), Noble et al. (2018).
*   **Core Realization insight:** Authority is conveyed entirely by the possession of an unforgeable reference rather than by evaluating an external access-control policy (ACL) or identity lookup table.
*   **Standard Formal Notation:** A capability graph $\mathcal{G} = (\mathcal{V}, \mathcal{E})$ where an edge $(v_i, v_j) \in \mathcal{E}$ denotes that domain $v_i$ holds a direct reference to invoke $v_j$.

### 3.2 Authorization Logics & Principals
*   **Mathematical Domain:** Inductive modal deductive systems where authority is modeled as logical assertions qualified by distinct semantic actors called principals.
*   **Landmark Literature Baselines:** Abadi, Burrows, Lampson, and Plotkin (1993, Taos Calculus), Garg and Pfenning (2006), Schneider, Morrisett, and Walsh (2011, Nexus Logic).
*   **Standard Formal Notation:** The modal judgment $\Gamma \vdash A \text{ says } \phi$, asserting that principal $A$ supports the truth or authorization of proposition $\phi$ under the logical context $\Gamma$.

### 3.3 Fractional and Separation Permissions
*   **Mathematical Domain:** Resource algebras constructed over partial commutative monoids, parameterizing raw heap pointer assertions with algebraic coefficients.
*   **Landmark Literature Baselines:** Reynolds (2002, Separation Logic), Boyland (2003, Fractional Permissions), Jung et al. (2018, Iris Framework).
*   **Standard Formal Notation:** $x \mapsto_\pi v$, where $\pi \in (0, 1]$ represents the fractional ownership coefficient (e.g., $\pi = 1$ denotes exclusive write authorization, while $\pi < 1$ denotes shared read authority).

### 3.4 Linear & Affine Ownership Systems
*   **Mathematical Domain:** Substructural intuitionistic type environments where structural rules for weakening and contraction are restricted, binding resources to distinct execution scopes.
*   **Landmark Literature Baselines:** Girard (1987, Linear Logic), Wadler (1990), Matsakis and Klock (2014, The Rust Borrow Checker).
*   **Standard Formal Notation:** A linear typing environment $\Delta$ mapping variables to substructural types, where $\Delta_1, \Delta_2$ represents the disjoint context split required for resource conservation.

### 3.5 Security Labels & Information Flow Control (IFC)
*   **Mathematical Domain:** Bounded, partially ordered sets or security lattices specifying directional information leakage constraints between domains.
*   **Landmark Literature Baselines:** Bell and LaPadula (1973), Denning (1976), Myers and Liskov (2000, Decentralized Label Model).
*   **Standard Formal Notation:** $\mathcal{L} = (S, \sqsubseteq)$, where a label $L_1 \sqsubseteq L_2$ dictates that data may flow from security clearance level $L_1$ to clearance level $L_2$.

### 3.6 Explicit Cryptographic Tokens & Access Contracts
*   **Mathematical Domain:** Serialized structures over algebraic cryptographic signature primitives, mapping identity keys to policy domains.
*   **Landmark Literature Baselines:** Rivest, Shamir, and Wagner (1996, SPKI/SDSI), Birrell, Needham, and Wobber (1998), Birgisson et al. (2014, Macaroon Token Frameworks).
*   **Standard Formal Notation:** $\text{Sign}_{K_{\text{issuer}}}(\text{Principal}, \text{Resource}, \text{Constraints})$.

### 3.7 Effect Systems and Capability Effects
*   **Mathematical Domain:** Type system structures extended with effect components that track the computational side-effects or system capabilities a term may invoke during evaluation.
*   **Landmark Literature Baselines:** Lucassen and Gifford (1988), Plotkin and Pretnar (2013, Algebraic Effects), Dolan et al. (2018), Brachthäuser et al. (2020, Capability Effects).
*   **Standard Formal Notation:** $\Gamma \vdash e : \tau \, ! \, \epsilon$, where $\epsilon$ denotes the bounded set of permitted effect labels or dynamic capabilities available during the evaluation of $e$.

## 4. The Authority Dimension Matrix
To clarify the exact functional roles played by these distinct mathematical representations, we map the dimensions of system control each paradigm enforces:

| Framework Paradigm | Controls Invocation | Controls Ownership | Controls Information Flow | Controls Identity | Controls Lateral Effects |
| --- | --- | --- | --- | --- | --- |
| **Object Capabilities** | Yes | Partial | No | No | No |
| **Separation Logic** | No | Yes | No | No | No |
| **Information Flow Control** | No | No | Yes | No | No |
| **Authorization Logics** | Yes | Partial | No | Yes | No |
| **Linear / Affine Types** | Partial | Yes | No | No | No |
| **Capability Effect Systems**| Yes | No | No | No | Yes |

## 5. Operational Evolution of Authority (Question 2)
Authority configurations fluctuate dynamically in response to computational progression. We isolate seven structural evolution pathways found across the literature:

*   **Creation (Minting):** The structural origination of fresh authority within an execution scope, such as allocating a new object reference, opening an isolated session channel, issuing a new cryptographic keypair, or generating a fresh proof witness.
*   **Delegation:** An authorized principal grants a subset of their active permissions to another entity without relinquishing their own access rights (e.g., SPKI delegation chains, discretionary access control propagation).
*   **Transfer:** The definitive shifting of an authority object from domain $\Omega_1$ to $\Omega_2$ such that it is structurally invalidated within $\Omega_1$ concurrently (e.g., linear resource consumption, move semantics).
*   **Borrowing:** The temporary allocation of an authority or resource reference to an execution scope, bounded by static lifetimes or stackframes, requiring explicit return or expiration (e.g., Rust's read/write borrow dynamics).
*   **Attenuation:** The deliberate down-scoping or restriction of an authority object before it is passed down an execution pathway, ensuring the recipient cannot access the broader parent capability space (e.g., object-capability wraps, Macaroon caveat compounding).
*   **Revocation:** The out-of-band or deterministic extraction/invalidation of an active authority allocation prior to its natural expiration (e.g., dynamic capability revocation via revocable proxies or membrane structures).
*   **Consumption:** The permanent destruction or transformation of a permission resource through active execution utilization (e.g., tokens consumed by a transaction step, token depletion via quotas).

## 6. Authority Validation Mechanisms (Question 3)
The enforcement of authority constraints is executed across three fundamental verification methodologies:

### 6.1 Static Validation
Authority properties are checked completely prior to runtime execution via linguistic structures, type checkers, or static analysis frameworks.
*   **Linguistic Primitives:** Substructural type systems, static effect tracking, and regional logic solvers.
*   **Strengths/Weaknesses:** Zero runtime overhead; however, it requires compile-time visibility of the complete program structure and cannot adapt dynamically to unpredictable, non-deterministic global environmental shifts.

### 6.2 Dynamic Validation
Verification occurs concurrently with execution steps, typically implemented via execution boundaries or out-of-band checking architectures.
*   **Linguistic Primitives:** Inline reference monitors, capability membranes, runtime contract enforcement, dynamic IFC tracking, monitor automata, policy decision points (PDP), and shield synthesis engines.
*   **Strengths/Weaknesses:** Resilient against high environmental unpredictability; however, it introduces non-zero runtime performance friction and risks hard runtime execution aborts if a constraint violation is encountered mid-transaction.

### 6.3 Hybrid Validation
Frameworks that combine static proof generation with explicit runtime checks.
*   **Linguistic Primitives:** Proof-Carrying Code (Necula 1997), Typed Assembly Language (Morrisett et al. 1999), proof-producing compilation, verified JIT compilers, typed intermediate languages, and gradual security typing models.
*   **Mechanics:** The derivation procedure constructs an explicit mathematical proof or witness demonstrating compliance with authority bounds. The runtime enforcement engine then performs a lightweight proof validation or replay step before executing the associated operational artifact.

## 7. Preserved Invariants and Safety Properties (Question 4)
The primary reason computer scientists employ authority semantics is to establish high-level preservation guarantees. The formal literature isolates five core invariants:

*   **Confinement:** Preventing an untrusted or isolated domain from propagating capability references or sensitive data outside an explicitly delimited boundary (Lampson 1973, Take-Grant protection models).
*   **Least Privilege:** Ensuring that an execution configuration possesses exclusively the minimal set of authority resources strictly required to complete its immediate computational task.
*   **Ownership Safety:** Proving the absolute absence of data races, dangling pointers, or concurrent modification conflicts over a shared mutable state space (e.g., separation logic invariants).
*   **Non-Interference:** Guaranteeing that low-security execution observers are mathematically incapable of detecting variations in high-security inputs (e.g., classic information flow properties).
*   **Delegation Soundness:** In this survey, we use "delegation soundness" as a descriptive umbrella for correctness properties ensuring that delegation mechanisms do not authorize effects beyond those justified by the originating authority model. Different communities formalize this property differently (e.g., logic cut-elimination, context monotonicity, policy containment).

## 8. Methodological Refinement: Interfacing with `08_Evaluation_Relations.md`
We explicitly refine our evaluation parameters regarding the interface between the Derivation Procedure ($\xrightarrow{\text{derive}}$) and the Enforcement Procedure ($\xrightarrow{\text{enact}}$) established in `08_Evaluation_Relations.md`:

> **The Structural Interface Invariant:**
> The separation between a derivation procedure and an enactment engine introduces an explicit semantic interface across which correctness and authority preservation properties must be formally maintained. If an adversary operating under the capability $c_{\text{arbitrary\_dev}}$ can substitute arbitrary operational artifacts ($\mathcal{A}$) at that exact interface, any authority guarantees established solely during the derivation phase ($\xrightarrow{\text{derive}}$) may no longer apply.

Consequently, the preservation of authority constraints across this boundary cannot be assumed globally; it must be explicitly established by verifying that the evaluated framework possesses a dedicated preservation relation (e.g., Type Preservation), a proof-carrying verification mechanism (e.g., PCC), or a continuous execution monitoring infrastructure (e.g., Runtime Verification shields) capable of binding $\mathcal{A}$ to the initial authority constraint object.

## 9. Open Conceptual Questions Feeding Downstream Modules
The insights extracted from this literature survey define three precise analytical vectors for the remaining preservation modules:

*   **Relational Property Mapping:** Under what conditions does the tracking of a dynamically evolving authority context ($\Lambda_t \xrightarrow{\text{step}} \Lambda_{t+1}$) require a relational hyperproperty over traces, versus collapsing into a standard trace safety property? (Evaluated in `Research/10_Preservation_Relations.md`)
*   **Monitor Sufficiency Analysis:** Can a pure runtime verification monitor operating under a Trace observer projection ($\mathcal{O}_{\text{trace}}$) enforce multi-principal delegation soundness without embedding a complete copy of the authorization logic solver inside the TCB? (Evaluated in `Research/13_Runtime_Assurance.md`)
*   **Admissibility Formulation:** Can a formal structural admissibility relation be defined between authority objects ($\Lambda_t$) and intermediate operational artifacts ($\mathcal{A}$) to encapsulate the invariants of both O-Cap confinement and capability effect typing without flattening their underlying differences? (Evaluated in `Research/07_Correspondence_Survey.md`)
