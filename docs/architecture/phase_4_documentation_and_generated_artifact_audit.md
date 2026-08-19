# Repository Coherence & Generated-Artifact Audit

> **Subsystem Target**: Phase 4 Routing & Dispatch Integration Audit  
> **Audit Version**: `1.0.0`  
> **Status**: `PASS` (All findings resolved or mitigated)

---

## 1. Documentation vs. Code Matching Audit

We audited all Phase 4 specifications against the actual Python classes, methods, and schemas in `cortex/tools/kernel/replica/router.py`, `lease.py`, `ledger.py`, and `identity.py`.

### 1.1 Stale Symbols and Diffs Remediation
* **`WorkerRef` Fields**: The specification mentioned `WorkerRef` as containing only metadata properties. The real implementation adds `required_capabilities` and `stage`.
  * *Status*: **MITIGATED** (Code contains a strict superset of the specification fields; compiler validation checks pass).
* **Stale Tool Paths in README**: Found `tools/cortex-verifier[.]py` (hyphenated) and `tests/conformance/fixtures/evidence_bundle_valid[.]json`.
  * *Remediation*: **PASS** (Corrected `README.md` to reference `tools/cortex_verifier.py` and `tests/golden/f4c_evidence_corpus/valid_chain.json`).
* **Docs Audit Automation**: Created `tools/assurance/docs_audit.py` to statically verify path existence, gate coverage, and Python syntax consistency. Integrated as Gate 6/6 in `./scripts/verify.sh`.

---

## 2. Code Example Classification

To prevent obsolete API code blocks from being confused with official implementation contracts, all markdown code blocks have been classified:

| Document | Code Block Context | Classification | CI Executable? |
| :--- | :--- | :--- | :---: |
| `phase_4_routing_and_dispatch_specification.md` | `WorkerRef` definition | ILLUSTRATIVE | No |
| `phase_4_routing_and_dispatch_specification.md` | `StateDomainKey` definition | ILLUSTRATIVE | No |
| `phase_5_load_balancing_specification.md` | $HardConstraints(W, I)$ formula | MATHEMATICAL | No |
| `README.md` | Dev quickstart code blocks | EXECUTABLE | Yes (via bash/python setup checks) |

---

## 3. CLI Generated Files Lifecycle & Inventory

Cortex enforces strict categorization rules for every file created or modified by CLI, runtime, or verification tools:

| Artifact | Created By | Classification | Git Tracked? | Expected Lifecycle |
| :--- | :--- | :--- | :---: | :--- |
| **assurance manifest** | release/assurance command | NORMATIVE | Yes | Persistent |
| **configuration spec** | CLI config init | NORMATIVE | Yes | Persistent |
| **effective config snapshot** | deployment CLI | GENERATED | No | Generation-scoped |
| **execution logs** | verification CLI | GENERATED | No | Run-scoped |
| **SQLite DB / WAL** | Gateway engine | RUNTIME | No | Persistent Runtime |
| **socket / PID files** | Gateway/worker process | RUNTIME | No | Process Lifetime |
| **pyc / python cache** | Python compiler | CACHE | No | Disposable |

### Invariant: Zero Silent Mutation of Source Code
Cortex CLI commands (`cortex deploy`, `cortex verify`, `cortex scale`) are strictly read-only regarding codebase source files, unit tests, and markdown documentation. No deployment operation is permitted to silently edit Git-tracked normative source code.

---

## 4. Generated File Isolation & Gitignore Cleanliness

All runtime-generated and cached files are isolated in private, ignored directories:
* `.runtime/` (process sockets, sqlite, active WALs)
* `.generated/` (intermediate config snapshots, test run outputs)
* `.cache/` (compiler/python cache)
* `.artifacts/` (run-scoped verification logs, release evidence packages)

### Verification Test: AUD-GEN-01
Running the entire suite of CLI operations and verification checks leaves the git workspace in a clean state:
```bash
./scripts/verify.sh
git diff --exit-code
git status --porcelain
# Returns exit code 0; zero untracked or modified files
```

---

## 5. Branch Contamination & Worktree Isolation

Switching between active branches (e.g. `feature/phase-4-routing-dispatch` and `feat/phase-5-load-balancing-design`) can lead to working-tree state contamination if intermediate cache/state files are shared.

### Mitigations
1. **Strict File Isolation**: No runtime-generated configuration or database files are written outside `.runtime/` or `.generated/`, both of which are listed in the repository `.gitignore`.
2. **Worktree Isolation Recommendation**: Developers working on concurrent phases (e.g., verifying Phase 4 while designing Phase 5) are advised to utilize `git worktree` to prevent local cross-contamination:
   ```bash
   git worktree add ../cortex-phase5 feat/phase-5-load-balancing-design
   ```

---

## 6. Identifier Scope & Ownership Matrix

| Identifier | Scope | Owner | Mutation Boundary | Never Used For |
| :--- | :--- | :--- | :--- | :--- |
| **ConfigGeneration** | Configuration Snapshot | Config Controller | Effective config changes | Lease ordering |
| **ConfigHash** | Exact config content identity | Config Controller | Content/bytes change | Temporal authority |
| **ReplicaGeneration** | Worker Deployment | Replica Controller | Worker replacement/rollout | Config identity |
| **LeaseEpoch** | Invocation Lineage | LeaseManager | Lease replacement | Global ordering |
| **LoadPolicyGeneration** | Routing Policy | Load Policy Controller | Policy configuration change | Execution authorization |
| **LoadPolicyHash** | Exact policy identity | Load Policy Controller | Policy content change | Lease fencing |

---

## 7. Configuration Precedence & Mutability Matrix

```text
  Defaults (pyproject.toml/code) 
         ▼
  Configuration File (cortex.yaml)
         ▼
  Environment Variables (CORTEX_*)
         ▼
  CLI Command Flags
```

All security-sensitive fields (such as sandbox profile settings, capability filters, and execution limits) cannot be overridden by CLI or environment variables during runtime. Changes to these parameters require the creation of a new `ConfigGeneration` and a rolling rollout of worker replicas.

---

## 8. Stacked Branch Topology & Semantics Protection

* **PR Branch Topology**:
  * `main` points to frozen RC1 (`9130291`).
  * PR #26 (`main` $\leftarrow$ `feature/phase-4-routing-dispatch`) implements Phase 4.
  * PR #27 (`feature/phase-4-routing-dispatch` $\leftarrow$ `feat/phase-5-load-balancing-design`) implements the Phase 5 design draft.
  * *Verdict*: **PASS** (Stacked branches prevent Phase 4 commits from muddying Phase 5 PR reviews, and protect main from unapproved code).
* **Semantics Protection**:
  * Checked all files in the Phase 5 branch (`feat/phase-5-load-balancing-design`).
  * Asserted that zero implementation code files (`lease.py`, `router.py`, `ledger.py`) were modified. Only `cortex_assurance_manifest.json` and `docs/architecture/phase_5_load_balancing_specification.md` were edited.
  * *Verdict*: **PASS** (Phase 4 authority boundaries remain completely unmodified).
