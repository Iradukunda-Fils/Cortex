# 08: Evaluation Relations
**Status:** LOCKED

## 1. Purpose and Scope
This document surveys how computation, execution planning, and optimization are formally modeled across distinct computer science paradigms. The core objective is to map the specific operational mechanics of the Derivation Procedure ($\xrightarrow{\text{derive}}$) and the Enforcement Procedure ($\xrightarrow{\text{enact}}$) as defined by different technical communities.

Rather than focusing on language syntax, this module analyzes how different formalisms translate semantic inputs into intermediate operational artifacts ($\mathcal{A}$) and how those artifacts dictate terminal execution effects ($e$). Every surveyed discipline is explicitly evaluated using the uniform criteria established in `11_Semantic_Objects.md` and contextualized under the parameterized threat metrics of `12_Threat_Model.md`.

## 2. Structural Paradigms of Evaluation
We classify the literature into four overarching operational families based on how they transition terms from intent to execution.

```text
                         [ EVALUATION PARADIGMS ]
                                    │
     ┌──────────────────────┬───────┴──────┬──────────────────────┐
     ▼                      ▼              ▼                      ▼
[ Inductive Reductions ] [ Compilation ] [ Plan Derivations ] [ Rewrite Systems ]
```

### 2.1 Inductive Reduction Systems (PL Semantics)
This tradition defines computation via structural manipulation of the language Abstract Syntax Tree (AST). The primary intermediate objects are concrete semantic steps or derivation proofs.

*   **Small-Step Operational Semantics (Structural Operational Semantics - SOS):** Introduced by Gordon Plotkin (1981), SOS defines execution via a localized transition relation ($\to$) mapping configurations to configurations.
    *   **Formal Notation:** $\langle c, \sigma \rangle \to \langle c', \sigma' \rangle$.
    *   **Mechanics:** The execution step is justified by an inductive rule system. The operational artifact $\mathcal{A}$ is a sequence of small-step derivation trees.
*   **Large-Step Operational Semantics (Natural Semantics):** Popularized by Gilles Kahn (1987), large-step semantics map a term directly to its final evaluation value.
    *   **Formal Notation:** $\langle c, \sigma \rangle \Downarrow \langle v, \sigma' \rangle$.
    *   **Mechanics:** The execution abstracts away intermediate machine states. The operational artifact $\mathcal{A}$ is a single, complete, finite derivation tree proving evaluation convergence.

### 2.2 Translation and Secure Compilation Frameworks
This family models evaluation as a sequence of linguistic transformations shifting code across abstract language boundaries.

*   **Compiler Intermediate Representations (IR):** Computations are lowered from high-level syntax into structured Control Flow Graphs (CFGs), Static Single Assignment (SSA) forms, or basic block topologies. $\mathcal{A}$ is the optimized intermediate program graph.
*   **Secure Compilation / Contextual Equivalence:** Pioneered by frameworks analyzing full abstraction (e.g., Abadi 1998, Patrignani et al. 2019), evaluation focuses on how a target language execution preserves source properties when linked against arbitrary, potentially adversarial target contexts ($\text{Ctx}_T$).
    *   **Formal Notation:** $P \approx_{\text{ctx}} Q \implies \llbracket P \rrbracket \approx_{\text{ctx}} \llbracket Q \rrbracket$.

### 2.3 Declarative Optimization & Plan Derivation Engines
Common in database query execution and distributed workflow frameworks, this paradigm completely decouples the definition of computed intent from the structural physical strategy used to execute it.

*   **Relational Query Algebra & Optimization:** Relational expressions are parsed into logical operator trees, processed by cost-based rewriting frameworks (e.g., Volcano/Cascades models), and compiled into physical query plans. The operational artifact $\mathcal{A}$ is a directed plan tree containing specific physical access paths (e.g., Index Scan, Hash Join).
*   **Distributed Workflow Schedulers:** Systems model execution plans as Directed Acyclic Graphs (DAGs) of tasks where vertices represent computational steps and edges represent data lineage or execution dependencies. $\mathcal{A}$ is the materialized scheduler schedule.

### 2.4 Rewrite Logics & Term Matching Systems
This family treats computation as continuous equational term substitution over highly structured state configurations.

*   **Rewriting Logic (Meseguer 1992):** Concurrent states are represented as elements of an algebraic equivalence class ($T_{\Sigma, E}$). Computation is modeled as the concurrent application of localized rewrite rules.
    *   **Formal Notation:** $[t]_E \to [t']_E$.
*   **Matching Logic / K Framework (Roșu 2010):** Language semantics are defined via structural configurations containing cell hierarchies (e.g., code cells, environment cells, heap cells). Evaluation is modeled as configuration matching and conditional rewriting. The operational artifact $\mathcal{A}$ is the execution configuration sequence.

## 3. Structural Evaluation Frameworks Analysis
To normalize these paradigms under our meta-design, each family is systematically analyzed across four operational axes: the mathematical definition of its derivation process ($\xrightarrow{\text{derive}}$), the structural form of its operational artifact ($\mathcal{A}$), the mechanics of its final enforcement stage ($\xrightarrow{\text{enact}}$), and its standard behavior under the granular attacker capabilities ($c_{\text{input\_mut}}$, $c_{\text{derive\_impl}}$, $c_{\text{arbitrary\_dev}}$) defined in `12_Threat_Model.md`.

### 3.1 Structural Operational Semantics (SOS)
*   **Derivation Mechanics ($\xrightarrow{\text{derive}}$):** The text parser and type-checker map text strings to structural syntax trees, matching them against inductive inference rules.
*   **Operational Artifact Form ($\mathcal{A}$):** An inductive derivation tree ($\mathcal{D}$) asserting a syntax step or evaluation convergence.
*   **Enforcement Mechanics ($\xrightarrow{\text{enact}}$):** An abstract machine or structural interpreter evaluates the tree by performing term reduction.
*   **Adversarial Vulnerability Matrix:**
    *   *Under $c_{\text{input\_mut}}$:* Attacker provides structurally valid but malicious program text; handled via traditional type boundaries.
    *   *Under $c_{\text{derive\_impl}}$:* Complete breakdown of language rules; the interpreter evaluates malformed semantic states that violate syntax definitions.
    *   *Under $c_{\text{arbitrary\_dev}}$:* Attacker injects a synthetic derivation tree directly into the step reduction phase, bypassing the language's formal derivation loop entirely.

### 3.2 Relational Algebra Plan Engines
*   **Derivation Mechanics ($\xrightarrow{\text{derive}}$):** Declarative SQL text is mapped to a logical tree, passed to an algebraic optimization engine, and transformed into a cost-optimized physical execution tree.
*   **Operational Artifact Form ($\mathcal{A}$):** A physical query plan operator tree or execution DAG.
*   **Enforcement Mechanics ($\xrightarrow{\text{enact}}$):** A physical storage engine and query processor loop (e.g., Volcano-style iterator model with `open()`, `next()`, `close()`) executes rows against physical blocks.
*   **Adversarial Vulnerability Matrix:**
    *   *Under $c_{\text{input\_mut}}$:* Traditional SQL injection; the text input manipulates the structure of the derived logical tree.
    *   *Under $c_{\text{derive\_impl}}$:* A compromised optimizer constructs an invalid query plan (e.g., missing mandatory security filtering predicates).
    *   *Under $c_{\text{arbitrary\_dev}}$:* The adversary injects a custom, raw physical plan tree directly into the query execution coordinator, bypassing all relational parsing and authorization checks.

### 3.3 Secure Compilation Models
*   **Derivation Mechanics ($\xrightarrow{\text{derive}}$):** A formal compiler lowers high-level source terms ($P$) to low-level target assembly terms ($\llbracket P \rrbracket$).
*   **Operational Artifact Form ($\mathcal{A}$):** Target language text, bytecodes, or binaries.
*   **Enforcement Mechanics ($\xrightarrow{\text{enact}}$):** Physical CPU hardware execution or an abstract target virtual machine executing instructions against an environment.
*   **Adversarial Vulnerability Matrix:**
    *   *Under $c_{\text{input\_mut}}$:* The compiler is fed malicious source code; verified via source language type checkers.
    *   *Under $c_{\text{derive\_impl}}$:* A compromised compiler actively introduces compiler bugs or optimization exploits (e.g., miscompiling out-of-bounds array assertions).
    *   *Under $c_{\text{arbitrary\_dev}}$:* An adversary links the compiled target code against an arbitrary, unverified target execution context ($\text{Ctx}_T$), attempting to leak internal state information via pointer corruption.

### 3.4 Rewriting Logic / Executable Language Frameworks (K Framework)
*   **Derivation Mechanics ($\xrightarrow{\text{derive}}$):** Terms are parsed and structurally matched against an equational configuration specification.
*   **Operational Artifact Form ($\mathcal{A}$):** An algebraic configuration term state ($t$).
*   **Enforcement Mechanics ($\xrightarrow{\text{enact}}$):** A transition engine performs logical matching and rewriting steps until arriving at an irreducible normal form.
*   **Adversarial Vulnerability Matrix:**
    *   *Under $c_{\text{input\_mut}}$:* The system is provided a valid term that drives the configuration into a known vulnerable state.
    *   *Under $c_{\text{derive\_impl}}$:* Compromise of the structural pattern matcher, causing it to execute incorrect configuration rewrites.
    *   *Under $c_{\text{arbitrary\_dev}}$:* The direct injection of a raw, malformed configuration term state directly into the rewrite engine, bypassing equation rules.

## 4. The Unified Evaluation Interface Crosswalk
To synthesize these distinct paradigms, we map their native nomenclatures directly onto our generalized operational transition primitives:

| Surveyed Community | Source Term ($I$) | Global Execution State ($\Sigma$) | Operational Artifact ($\mathcal{A}$) | Derivation Procedure ($\xrightarrow{\text{derive}}$) | Enforcement Procedure ($\xrightarrow{\text{enact}}$) |
| --- | --- | --- | --- | --- | --- |
| **SOS / Natural Semantics** | Program Expressions ($e$) | Variable Store / Memory Heap ($\sigma$) | Derivation Tree ($\mathcal{D}$) | Abstract Parse & Type Elaboration | Structural Step Reduction ($\to$) |
| **Secure Compilation** | Source Program ($P$) | Compiler Environment | Target Binaries ($\llbracket P \rrbracket$) | Source-to-Target Compilation | Target Machine Hardware Dispatch |
| **Relational Database Systems** | Declarative Query String | Database Catalog & Relations | Physical Query Plan | Cost-Based Algebraic Optimization | Storage Engine Row Iterator Loop |
| **Distributed Schedulers** | Job Pipeline Intent | Cluster Resource State | Task Dependency DAG | DAG Scheduling & Topological Sorting | Worker Node Task Execution |
| **Rewriting Logic / K** | Initial Program Term | Cell Configuration | Configuration State ($t$) | Structural Configuration Parsing | Conditional Pattern Rewriting ($\xrightarrow{\ast}$) |

## 5. Primary Analytical Synthesis
By surveying these computational evaluation paradigms, a vital cross-cutting structural property emerges:

> **The Separation Invariant:**
> Across all high-performance or declarative execution landscapes (compilers, databases, distributed engines), the derivation procedure $\xrightarrow{\text{derive}}$ is deliberately decoupled from the enforcement procedure $\xrightarrow{\text{enact}}$ to permit intensive structural optimizations or resource scheduling. Consequently, the operational artifact $\mathcal{A}$ represents a distinct mathematical interface.

This structural decoupling creates a severe vulnerability under the adversary capability $c_{\text{arbitrary\_dev}}$. If a system's safety or authority guarantees are evaluated exclusively during the derivation phase $\xrightarrow{\text{derive}}$ under a White-box observer projection ($\mathcal{O}_{\text{white}}$), the entire security argument collapses if an attacker can directly inject a malformed operational artifact $\mathcal{A}$ into an enactment engine operating under a restricted Artifact observer projection ($\mathcal{O}_{\text{art}}$).

## 6. Open Semantic Questions
The findings of this evaluation survey establish three core questions that must be tracked through the subsequent modules:

*   How do authority-confinement models natively handle frameworks where the derivation procedure $\xrightarrow{\text{derive}}$ generates an operational artifact $\mathcal{A}$ that dynamically synthesizes new sub-computations during the enactment phase $\xrightarrow{\text{enact}}$?
*   Can a target language transition relation ($\to$) inside a secure compilation model be configured to treat the delegation context $\Lambda_t$ as an explicit operational boundary without converting the compiler into a complete reference monitor?
*   What formal definitions of structural correctness exist to prove that an optimized operational artifact $\mathcal{A}_{\text{optimized}}$ preserves the exact delegation boundaries of its source artifact $\mathcal{A}_{\text{source}}$ when evaluated over an unpredictable, non-deterministic global execution state $\Sigma$?
