# 11: Semantic Objects
**Status:** LOCKED  

## Purpose
Catalog the specific mathematical and logical categories operated on by different computer science communities. Preventing category errors when comparing objects that live in fundamentally incompatible semantic spaces.

## Dependencies
*   [02_Domain_Model.md](02_Domain_Model.md)
*   [03_Terminology.md](03_Terminology.md)

---

## 1. Unified Mathematical Space Comparison

We partition the mathematical universe (Semantic Domain) from the specific entity manipulated inside that universe (Primary Semantic Object). This prevents category errors when analyzing verification mappings.

### Mathematical Landscape of Semantic Domains and Objects

| Community / Tradition | Semantic Domain (Space) | Primary Semantic Object |
| --- | --- | --- |
| **Structural Operational Semantics** | Inference Rule Systems & Derivation Woods | Derivation Tree ($\mathcal{D}$) |
| **Abstract Machines** | Product Space of State Configurations | Machine State Configuration ($c$) |
| **Trace Semantics** | Languages over Transition Action Alphabets ($\Sigma^*$) | Sequence Trace ($\tau$) |
| **Program Logics (Hoare)** | First-Order Predicate Space over Valuations | State Assertion Formula ($P, Q$) |
| **Separation Logic** | Monoidal Spatial Heap Model | Spatial Heap Predicate ($\phi * \psi$) |
| **Capability Systems** | Protection Graphs / Connectivity Matrices | Reference Capability Edge ($c$) |
| **Authorization Logics** | Deductive Context Spaces | Logical Statement Judgment ($K \text{ says } \phi$) |
| **Data & System Provenance** | Ancestral Dependency Spaces | Directed Acyclic Graph ($\mathcal{G}$) |
| **Information Flow Control** | Security Clearance Posets / Lattices ($\mathcal{L}, \sqsubseteq$) | Labeled State Variable ($x_L$) |
| **Secure Compilation** | Contextual Interaction Quantifiers | Target-to-Source Context Pair ($\text{Ctx}_T, \text{Ctx}_S$) |
| **Proof-Carrying Code** | Typed $\lambda$-Calculus Terms / Invariant Envelopes | Proof Term Object ($M$) |
| **Rewriting Logic** | Equational Equivalence Classes ($T_{\Sigma, E}$) | Equational State Term ($t$) |

---

## 2. Category Error Mitigation

By mapping these categories, we can resolve why standard compositions fail:
*   **The Provenance-to-Logic Gap**: Data Provenance operates on post-facto Lineage Graphs ($\mathcal{G}$). Program Logics operate on Assertions/Predicates ($P, Q$). Conflating them results in systems that trace history but cannot evaluate logical consequences.
*   **The Capability-to-Authorization Gap**: Capability Systems operate on Protection Graphs (structural reachability). Authorization Logics operate on Logical Judgments ($K \text{ says } \phi$). Merging them requires a semantic bridge that maps structural paths to logical warrants.
*   **The Interpretation Boundary Gap**: In an interpreted environment, the host type system reasons about the Machine Configuration of the interpreter. The program running inside the interpreter has its own execution trace that exists within a nested virtual structure. This mismatch prevents the outer system's type assertions from directly bounding the inner program's logical actions.
