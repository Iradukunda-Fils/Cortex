# 11: Semantic Objects
**Status:** LOCKED  

## Purpose
Catalog the specific mathematical and logical categories operated on by different computer science communities. Preventing category errors when comparing objects that live in fundamentally incompatible semantic spaces.

## Dependencies
*   [02_Domain_Model.md](02_Domain_Model.md)
*   [03_Terminology.md](03_Terminology.md)

---

## 1. Unified Mathematical Space Comparison

We isolate and define the objects manipulated by various academic bodies. This establishes that the abstract **Operational Artifact ($\mathcal{A}$)** and the **Delegation Context ($\Lambda$)** represent a unique combination of structural mapping and credential bounds.

### Semantic Community Object Catalog

| Semantic Community / Framework | Primary Semantic Object Manipulated | Formal Mathematical Category |
| --- | --- | --- |
| **Structural Operational Semantics** | Derivation Tree | Inductive proof object over inference rules |
| **Abstract Machines** | Machine Configuration | Product space of registers, control stacks, and memory heaps |
| **Trace Semantics** | Execution Trace | Linear sequence or tree of state transitions ($\sigma_0 \xrightarrow{a_0} \sigma_1$) |
| **Program Logics (Hoare / Separation)** | Assertions / Heap Predicates | First-order logic predicates over valuation environments or spatial resources |
| **Capability Systems** | Capability / Protection Graph | Directed graph mapping principals to objects via unforgeable reference edges |
| **Authorization Logics** | Logical Judgment | Formal deductive assertions anchored by a principal (e.g., $K \text{ says } \phi$) |
| **Data & Whole-System Provenance** | Lineage Graph | Directed Acyclic Graph (DAG) recording post-facto execution history dependencies |
| **Information Flow Control (IFC)** | Labeled States / Security Lattice | Poset of security clearances tracking information dependency bounds |
| **Secure Compilation** | Context Pair / Behavioral Traces | Quantified interaction sequences between target execution contexts and programs |
| **Proof-Carrying Code (PCC)** | Proof Term / Typing Witness | Typed $\lambda$-calculus terms or formal checking tokens |
| **Rewriting Logic (Institutional)** | Rewrite Term / Equational State | Equational equivalence classes modulated by rewriting rules ($t \to t'$) |

---

## 2. Category Error Mitigation

By mapping these categories, we can resolve why standard compositions fail:
*   **The Provenance-to-Logic Gap**: Data Provenance operates on post-facto Lineage Graphs, which are directed acyclic graphs. Program Logics operate on Assertions/Predicates. Conflating them results in systems that trace history but cannot evaluate logical consequences.
*   **The Capability-to-Authorization Gap**: Capability Systems operate on Protection Graphs (structural reachability nodes). Authorization Logics operate on Logical Judgments (says-calculus expressions). Merging them requires a semantic bridge that maps structural paths to logical warrants.
*   **The Interpretation Boundary Gap**: In an interpreted environment, the host type system reasons about the Machine Configuration of the interpreter. The program running inside the interpreter has its own execution trace that exists within a nested virtual structure. This mismatch prevents the outer system's type assertions from directly bounding the inner program's logical actions.
