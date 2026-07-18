# 12: Threat Model
**Status:** LOCKED

## 1. Purpose
This document establishes the structural and adversarial assumptions under which all subsequent semantic claims and literature evaluations in this research program are interpreted. The objective is not to design a specific security architecture or model a concrete production exploit vector. Instead, this document provides a normalized execution and threat model that permits a mathematically rigorous comparison across disparate disciplines—specifically operational semantics, authorization systems, secure compilation, runtime verification, and preservation frameworks.

Throughout the remainder of this work, every preservation relation, simulation argument, and hyperproperty statement is interpreted relative to the parameters defined here unless explicitly stated otherwise.

## 2. Modeling Philosophy
To prevent the common conflation of implementation-specific behavior with algebraic properties, this research agenda enforces a strict separation between three orthogonal concerns:

```text
┌─────────────────────────────────┐
│     MATHEMATICAL SEMANTICS      │ ──► Documents 07–11: Define mathematical domains and objects.
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│     EXECUTION ARCHITECTURE      │ ──► Document 13: Defines runtime observation/enforcement mechanics.
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│       THREAT ASSUMPTIONS        │ ──► Document 12 (This Document): Defines environmental boundaries.
└─────────────────────────────────┘
```

By isolating threat assumptions into this dedicated module, we ensure that our semantic evaluations remain highly objective. Rather than declaring a framework "insecure" or "insufficient" because it fails under a specific system vulnerability, we map its precise boundaries by identifying the exact configuration of trusted components and observer projections it requires to maintain its invariants.

## 3. System Model
We abstract execution across all target paradigms (programming languages, database engines, workflow coordinators, interpreters, and distributed schedulers) using a generalized operational transition notation:

$$\frac{\Sigma; \Lambda_t \vdash I \xrightarrow{\text{derive}} \mathcal{A} \quad \quad \Sigma; \Lambda_t \vdash \mathcal{A} \xrightarrow{\text{enact}} e}{\Sigma; \Lambda_t \vdash I \Longrightarrow e}$$

Where:
*   $\Sigma \in \text{StateDomain}$ represents the global execution state (e.g., memory heaps, environment variables, database relations, network state).
*   $\Lambda_t \in \text{AuthDomain}$ denotes the abstract Delegation Context or constraint object at execution time $t$.
*   $I \in \text{InputStream}$ represents the sequence of incoming external inputs or requests.
*   $\mathcal{A} \in \text{ArtifactDomain}$ represents the intermediate Operational Artifact (e.g., AST, physical query plan, compiler intermediate representation, optimization trace, or proof term).
*   $e \in E_{\text{irreversible}}$ denotes the terminal, externally observable, and irreversible effect.

## 4. Parameterized Trusted Computing Base (TCB)
Rather than assuming a single fixed configuration of trust, this framework parameterizes the Trusted Computing Base as a three-tuple:

$$\text{TCB} = (T_H, T_S, T_C)$$

*   $T_H$: **Hardware Assumptions**
    The architectural security boundaries guaranteed by the underlying physical layer (e.g., strong hardware memory isolation, unforgeable cryptographic key storage, hardware-enforced privilege rings, or Trusted Execution Environments / enclaves).
*   $T_S$: **System Assumptions**
    The environmental components managed by the operating platform (e.g., kernel page table isolation, hypervisor separation, process scheduler integrity, or immutable filesystem boundaries).
*   $T_C$: **Computational Assumptions**
    The software components responsible for linguistic or mathematical validation (e.g., the correctness of an input parser, the safety of a type checker, the logical core of a theorem prover, or the implementation of an inline reference monitor).

**Core Research Baseline:** This program explicitly avoids assuming that arbitrary user-space optimization routines or planning algorithms belong to the TCB. A primary goal of the upcoming surveys is evaluating how frameworks maintain invariants when $\xrightarrow{\text{derive}}$ occurs entirely within an untrusted context.

## 5. Observation Model
We define adversarial visibility strictly as a projection function over the complete execution tuple. Let $X$ represent the total execution space:
$$X = \langle I, \Sigma, \Lambda_t, \mathcal{A}, \tau, e \rangle$$

Where $\tau$ is the internal sequence of step-by-step state transitions. An observer $\mathcal{O}$ is defined as a projection mapping from the total space to a visible evaluation alphabet $V$:
$$\mathcal{O} : X \longrightarrow V$$

Using this projection approach, we formalize the standard observation configurations found across the literature:

| Observer Model (O) | Projected (Visible) Components | Target Literature Paradigm |
| --- | --- | --- |
| **Black-box Observer** ($\mathcal{O}_{\text{black}}$) | $\{e\}$ | Standard End-to-End Reference Monitors |
| **Trace Observer** ($\mathcal{O}_{\text{trace}}$) | $\{\tau, e\}$ | Secure Compilation, Non-Interference, IFC |
| **Artifact Observer** ($\mathcal{O}_{\text{art}}$) | $\{\mathcal{A}, e\}$ | Query Optimization, Proof-Carrying Code |
| **White-box Observer** ($\mathcal{O}_{\text{white}}$) | $\{I, \Sigma, \Lambda_t, \mathcal{A}, \tau, e\}$ | Complete System Verifier / Intra-Enclave |

## 6. Authority Dynamics
To prevent our threat baseline from biasing the research toward a specific authorization philosophy, we formalize the temporal properties of the delegation context ($\Lambda_t$) across four distinct operational models:

*   **Immutable Authority:** $\Lambda_t = \Lambda_0$. The authority allocation remains completely static over the execution lifetime (e.g., cryptographically signed capability tokens, static role-based policies).
*   **Stateful Authority:** $\Lambda_t \xrightarrow{\text{step}} \Lambda_{t+1}$. The delegation context changes deterministically based on internal execution milestones (e.g., consumption of resource quotas, temporal lease expirations, inline dynamic privilege attenuation).
*   **External Authority:** The delegation context mutates non-deterministically relative to the internal execution loop via out-of-band events (e.g., asynchronous administrator revocations, live policy server updates, distributed admission control adjustments).
*   **Observational Authority:** $\Lambda_t$ is never actively processed or mutated by the execution engine. Instead, authorization is evaluated dynamically as an external structural predicate over state transitions: $\Sigma \models \text{Allowed}(\Lambda_t, e)$.

## 7. Attacker Capability Model
Rather than cataloging ephemeral exploit variants, the adversary is characterized as an element inhabiting a powerset of precise primitives. Let $\mathcal{C}$ define the universal set of attacker capabilities:
$$\mathcal{C} = \{c_1, c_2, \dots, c_n\}$$
Individual system configurations select a specific subset of $\mathcal{C}$ to represent their target threat landscape:

*   $c_{\text{input}}$: Ability to inject arbitrary, non-deterministic payloads into the input stream $I$.
*   $c_{\text{inspect\_trace}}$: Ability to read the fine-grained execution trace $\tau$ (microarchitectural leakage, debugging hooks).
*   $c_{\text{replay}}$: Ability to duplicate and resubmit historical valid transaction tokens.
*   $c_{\text{mutate\_user}}$: Ability to modify unprivileged user-space memory segments during active execution.
*   $c_{\text{compromise\_derive}}$: Ability to fully manipulate the derivation procedure $\xrightarrow{\text{derive}}$, resulting in arbitrary malformed operational artifacts $\mathcal{A}$.
*   $c_{\text{delay}}$: Ability to introduce arbitrary temporal delays or reorder concurrent messaging structures.
*   $c_{\text{corrupt\_state}}$: Ability to violently alter execution state parameters $\Sigma$ outside the formal semantics of the target language.

## 8. Explicit Integrity Assumptions
Every semantic preservation theorem relies on an explicit set of structural invariants. Subsequent surveys will map which of the following integrity parameters are strictly required by each framework:

*   **Memory Confinement:** Address spaces are strongly isolated; out-of-bounds pointer manipulation is structurally impossible.
*   **Capability Unforgeability:** Reference capabilities cannot be manufactured or modified via bitwise manipulation.
*   **Cryptographic Soundness:** Cryptographic primitives are mathematically resilient against polynomial-time decryption or signature forgery.
*   **Evaluation Determinism:** Given identical configurations of $\Sigma$, $\Lambda$, and $I$, the execution engine transitions through identical trace pathways.
*   **Linguistic Type Safety:** The execution context guarantees that terms match their static or dynamic behavioral invariants.

## 9. Environmental Nondeterminism vs. Adversarial Interference
This framework strictly partitions non-deterministic execution variance from active adversarial manipulation. Environmental nondeterminism stems from platform characteristics that do not actively seek to invalidate security properties, including:
*   Concurrent thread interleavings driven by the operating system scheduler.
*   Network latency variances across distributed physical nodes.
*   Hardware interrupt timings.
*   Randomized initialization parameters within randomized verification routines.

This distinction is mathematically vital: many foundational PL preservation results (such as simulation relations and contextual equivalence) are designed to tolerate complex environmental nondeterminism while collapsing completely under deliberate adversarial interference ($c_{\text{compromise\_derive}}$).

## 10. Scope Exclusions
Unless explicitly introduced by a highly localized system case study, the following execution phenomena remain outside the scope of this formal research program:
*   **Speculative Execution & Transient State Side-Channels:** Microarchitectural attacks targeting out-of-order execution boundaries (e.g., Spectre, Meltdown).
*   **Physical Hardware Compromise:** Fault-injection attacks, physical probing, differential power analysis, or direct electromagnetic eavesdropping.
*   **Coarse Denial-of-Service (DoS):** Attacks whose sole objective is resource exhaustion without attempting to cause unauthorized effects or bypass delegation constraints.
*   **Probabilistic Cryptographic Failures:** Negligible-probability hash collisions or prime factorization breakthroughs.

## 11. Threat Model Dimensions Matrix
The complete parameterized environment is structurally summarized below:

| Dimension | Scope of Formal Parameterization |
| --- | --- |
| **Execution Model** | Abstract operational transition: $\Sigma; \Lambda_t \vdash I \xrightarrow{\text{derive}} \mathcal{A} \xrightarrow{\text{enact}} e$ |
| **TCB Specification** | Parameterized tuple: $\text{TCB} = (T_H, T_S, T_C)$ |
| **Observer Model** | Projections over the total execution space: $\mathcal{O} : X \longrightarrow V$ |
| **Authority Evolution** | Categorized behavior: $\{\text{Immutable}, \text{Stateful}, \text{External}, \text{Observational}\}$ |
| **Adversary Strategy** | Configurable capability vector drawn from the powerset of $\mathcal{C}$ |
| **Environment Dynamics** | Partitioned behavior: Deterministic / Nondeterministic / Adversarial |
| **Integrity Boundaries** | Explicitly declared invariants required for structural proof convergence |
| **Out-of-Scope Risks** | Physical, side-channel, and resource exhaustion phenomena |

## 12. Primary Research Inquiries Enabled by this Model
With the structural ontology (`11_Semantic_Objects.md`) and the environmental threat baseline (`12_Threat_Model.md`) formally established, the remaining literature surveys are equipped to answer the core analytical questions of this research program:

*   **Observer Resilience:** Which classic semantic preservation relations remain valid when shifted from a White-box observer projection ($\mathcal{O}_{\text{white}}$) down to an Artifact observer projection ($\mathcal{O}_{\text{art}}$) or Trace observer projection ($\mathcal{O}_{\text{trace}}$)?
*   **Authority Dynamic Support:** Which existing formal frameworks natively parameterize their preservation proofs over a stateful or externally mutating authority context ($\Lambda_t \xrightarrow{\text{step}} \Lambda_{t+1}$)?
*   **TCB Decoupling Capacity:** Under what exact software and hardware integrity assumptions can an authority preservation claim be formally checked independently of the primary execution engine?
*   **Adversarial Collapse Boundaries:** Which specific attacker capability selections within $\mathcal{C}$ mathematically invalidate traditional compiler correctness simulations, and do those boundaries match the requirements of system-level delegated workflows?
*   **Subsumption Verification:** Does any existing semantic framework directly characterize the preservation of authority-constrained, externally observable effects ($e$) when the intermediate operational artifact ($\mathcal{A}$) is synthesized inside a completely untrusted environment ($c_{\text{compromise\_derive}}$)?
