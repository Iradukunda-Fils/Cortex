# Cortex Release Accounting & Tag Normalization Register
**Canonical Release Tag Registry, Commit Relationships, and Artifact Hashes**  
**Date:** August 22, 2026  
**Repository Baseline SHA:** `c9d72d3` (`main`)

---

## 1. Release Tag Disambiguation & Alias Reconciliation

To prevent governance drift, historical release tags are categorized into canonical production releases, release candidates, and experimental milestones:

- **`v0.4.0rc1` (CANONICAL CURRENT RELEASE CANDIDATE):** Points to the complete Phase 4 Routing & Dispatch Subsystem plus Issue #30 Control Plane Configuration Resolver (`c9d72d3`). Package version in `pyproject.toml` is `0.4.0`.
- **`v0.4.0-experimental` (HISTORICAL EXPERIMENTAL TAG):** Early milestone tag created during initial Phase 4 development (`012b095`). Superseded by `v0.4.0rc1`.
- **`v0.3.0` / `v0.3.0-experimental-rc1` (PHASE 3 / MULTI-PROCESS RUNTIME):** Sealed evidence release for multi-process worker supervision, IPC framing, and CA-001..CA-003.
- **`v0.2.1` (CANONICAL PRODUCTION RELEASE):** Latest production release tag on GitHub, published with Apache-2.0 open-source governance.

---

## 2. Canonical Release Accounting Ledger

| Field | Release v0.2.1 | Release v0.3.0-rc1 | Release v0.4.0rc1 |
| :--- | :--- | :--- | :--- |
| **Release ID** | `REL-V0.2.1` | `REL-V0.3.0-RC1` | `REL-V0.4.0-RC1` |
| **Git Tag** | `v0.2.1` | `v0.3.0-experimental-rc1` | `v0.4.0rc1` |
| **Commit SHA** | `15e8b2a` | `8d8dd67` | `c9d72d3` |
| **Manifest Hash** | `e3b0c44298fc...` | `dfad89f5cc01...` | `0ac0707e9b23...` |
| **Evidence Package** | Standard regression suite | `artifacts/release_candidates/v0.3.0-experimental-rc1` | `docs/architecture/coq_print_assumptions_audit.json` |
| **Schema Version** | Draft 2020-12 | Draft 2020-12 | Draft 2020-12 (`cortex/schemas/v1`) |
| **Toolchain** | Python 3.10+ | Python 3.10+, Go 1.20+, Rust 1.70+ | Python 3.10+, Go 1.20+, Rocq 9.1, Verilator 5.0 |
| **Pytest Count** | 208 tests | 278 tests | **341 tests** |
| **Certification Count** | 74 checks | 104 checks | **136 checks** |
| **Operational Status**| `PRODUCTION_STABLE` | `SEALED_EXPERIMENTAL` | `CURRENT_MAINLINE_BASELINE` |
