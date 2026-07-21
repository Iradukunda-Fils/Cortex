# Cortex Spatiotemporal Logical Relation — Artifact Evaluation Guide

This directory contains the mechanized Rocq/Coq proof suite for the Cortex spatiotemporal authority verification framework.

## Quick Start (Kick-the-Tires Phase ~ 2 Minutes)

To build the container and run the automated verification script:

```bash
# 1. Build the Docker image
docker build -t cortex-verification .

# 2. Run the audit container
docker run --rm cortex-verification
```

The script will compile all `.v` modules, search for `Admitted` placeholders, execute `Print Assumptions` on all key theorems, and output `audit_results.log`.

## Detailed Evaluation Guide (Manual Step-by-Step)

If you prefer to inspect and compile the development manually using a local Coq installation:

### Prerequisites
- **Rocq / Coq**: Version 9.0+ or 9.1+
- **Build System**: `make`

### 1. Build the Proof Pipeline
Run `make` to compile all modules in topological dependency order:

```bash
make clean
make
```

**Expected Result**: All `.v` files (`World.v` → `Semantics.v` → `LogicalRelation.v` → `FTLR.v` → `Soundness.v` → `Substitution.v`) compile cleanly with exit code 0.

### 2. Verify Absence of Admitted Lemmas
To check that no proofs rely on unproven placeholders:

```bash
grep -rn "Admitted" *.v
```

**Expected Result**: Exit code 1 (zero matches returned).

### 3. Transitive Dependency & Axiom Audit
To run the kernel's `Print Assumptions` check interactively or via `coqtop`:

```coq
From Cortex Require Import Soundness.
From Cortex Require Import Substitution.

(* Core Soundness Pipeline *)
Print Assumptions unified_soundness.
Print Assumptions fundamental_theorem.

(* Context Substitution Infrastructure *)
Print Assumptions semantic_substitution_preserves_typing.
Print Assumptions V_w_monotonicity.
```

- **Core Soundness Results**: `unified_soundness` and `fundamental_theorem` return `Closed under the global context` (100% axiom-free core safety path).
- **Monotonicity Infrastructure**: `V_w_monotonicity` lists `Axioms: valid_cap_decay_axiom`, reflecting the isolated domain parameter governing capability decay under world transitions ($w \sqsubseteq w'$).

### Decoupled Architecture Summary
```
================================================================================
 CORE SOUNDNESS PIPELINE (CLOSED)             SUBSTITUTION & MONOTONICITY
================================================================================
 World.v                                      Substitution.v
 Semantics.v                                     ├── context_weakening (Closed)
 LogicalRelation.v                              ├── semantic_subst (Closed)
 FTLR.v (fundamental_theorem)                    └── V_w_monotonicity
 Soundness.v (unified_soundness)                      └── valid_cap_decay_axiom
================================================================================
```
