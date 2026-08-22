# Cortex Documentation Inventory & Classification Register
**Authoritative Documentation Asset Catalogue**  
**Date:** August 22, 2026  
**Repository Baseline SHA:** `1927eb4` (`main`)

---

## 1. Documentation Inventory & Classification Table

| Path | Title | Purpose | Classification | Normative? | Canonical? | Referenced? | Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `README.md` | Cortex System Overview | Root entrypoint and system architecture summary | `CANONICAL_ARCHITECTURE` | Yes | Yes | Yes | Retain as Canonical |
| `docs/README.md` | Documentation Index | Master documentation directory & guide index | `CANONICAL_GOVERNANCE` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/cortex_system_architecture_current.md` | System Architecture | End-to-end 15-stage pipeline & security architecture | `CANONICAL_ARCHITECTURE` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/configuration_and_control_plane_specification.md` | Configuration Specification | Field-class normalization, CLI/ENV precedence, persistence | `CANONICAL_SPECIFICATION` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/invocation_ledger_compaction_design.md` | Ledger Compaction Design | InvocationLedger snapshot compaction, header schema, recovery | `CANONICAL_SPECIFICATION` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/phase_4_routing_and_dispatch_specification.md` | Phase 4 Specification | Routing, dispatch, candidate evaluation, worker state | `CANONICAL_SPECIFICATION` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/phase_5_load_balancing_specification.md` | Phase 5 Load Balancing Spec | Dynamic load balancing engine & health probe spec | `CANONICAL_SPECIFICATION` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/replica_scaling_specification.md` | Replica Scaling Specification | Multi-worker process isolation & sandbox bounds | `CANONICAL_SPECIFICATION` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/threat_model.md` | Runtime Threat Model | Security boundaries, trust domains, attack vectors | `CANONICAL_ARCHITECTURE` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/api-stability-policy.md` | API Stability Policy | SDK backward compatibility guarantees & deprecation rules | `CANONICAL_GOVERNANCE` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/canonical-serialization.md` | Canonical Serialization | CBE binary encoding determinism & stream framing | `CANONICAL_SPECIFICATION` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/code_quality_policy.md` | Code Quality Policy | Style, linting, typing, test coverage standards | `CANONICAL_GOVERNANCE` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/commit_quality_policy.md` | Commit Quality Policy | Git commit message standards & PR workflow | `CANONICAL_GOVERNANCE` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/contributor_security_boundaries.md` | Contributor Security Bounds | Sandbox constraints & contributor access rules | `CANONICAL_GOVERNANCE` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/cortex_completed_work_register.md` | Completed Work Register | Authoritative historical ledger of completed engineering tasks | `CANONICAL_ASSURANCE` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/cortex_open_work_register.md` | Open Work Register | Authoritative backlog of outstanding engineering debt & tasks | `CANONICAL_ROADMAP` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/cortex_current_repository_inventory.md` | Repository Inventory | Catalogue of physical/logical assets & trust domain levels | `CANONICAL_OPERATIONAL` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/cortex_release_accounting_register.md` | Release Accounting Register | Canonical release registry disambiguating tags | `CANONICAL_GOVERNANCE` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/cortex_github_full_state_audit.md` | GitHub State Audit | Reconciled state audit across GitHub issues/PRs and commits | `CANONICAL_ASSURANCE` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/verification_closure_matrix.md` | Verification Matrix | Gate A-L compliance status & theorem closure matrix | `CANONICAL_ASSURANCE` | Yes | Yes | Yes | Retain as Canonical |
| `docs/architecture/coq_formal_proof_inventory_delta.md` | Coq Proof Inventory Delta | Proof inventory breakdown across 24 Coq files | `HISTORICAL_AUDIT` | No | No | Yes | Archive / Retain |
| `docs/architecture/cortex_github_issue_number_audit.md` | GitHub Sequence Audit | Audit of unified issue/PR sequence numbers 1-38 | `HISTORICAL_AUDIT` | No | No | Yes | Archive / Retain |
| `docs/architecture/cortex_github_remote_reconciliation.md` | Remote Reconciliation | Git remote reconciliation log for PR #38 and main | `HISTORICAL_AUDIT` | No | No | Yes | Archive / Retain |
| `docs/architecture/reconstruction_audit_log.md` | Reconstruction Audit Log | Step-by-step 12-stage system reconstruction log | `HISTORICAL_AUDIT` | No | No | Yes | Archive / Retain |
| `docs/architecture/phase_1_3_implementation_audit.md` | Phase 1-3 Audit | Historical audit report for Phases 1 through 3 | `HISTORICAL_AUDIT` | No | No | Yes | Archive / Retain |
| `docs/architecture/phase_4_branch_readiness_review.md` | Phase 4 Readiness Review | Historical review for Phase 4 branch integration | `HISTORICAL_AUDIT` | No | No | Yes | Archive / Retain |
| `docs/architecture/phase_4_documentation_and_generated_artifact_audit.md` | Phase 4 Documentation Audit | Historical audit report for Phase 4 documentation | `HISTORICAL_AUDIT` | No | No | Yes | Archive / Retain |
| `docs/architecture/phase_4_implementation_audit.md` | Phase 4 Implementation Audit | Historical implementation audit report for Phase 4 | `HISTORICAL_AUDIT` | No | No | Yes | Archive / Retain |
| `docs/architecture/cli_and_configuration_audit.md` | CLI & Config Audit | Temporary audit report for Issue #30 configuration resolver | `DUPLICATE` | No | No | Yes | Merge & Archive |
| `docs/architecture/configuration_standardization_audit.md` | Config Standardization Audit | Duplicate audit report for Issue #30 configuration resolver | `DUPLICATE` | No | No | No | Merge & Remove |
| `docs/architecture/cortex_repository_architecture_audit.md` | Early Architecture Audit | Duplicate early audit report superseded by current architecture | `STALE` | No | No | Yes | Archive |
| `docs/architecture/cortex_systems_review_and_phase2_roadmap.md` | Systems Review & Roadmap | Superseded early roadmap superseded by issue roadmap | `STALE` | No | No | Yes | Archive |
| `docs/architecture/cortex_future_implementation_plan.md` | Future Implementation Plan | Superseded plan superseded by open work register | `STALE` | No | No | Yes | Archive |
| `docs/architecture/cortex_experimental_release_plan.md` | Experimental Release Plan | Superseded release plan superseded by release register | `STALE` | No | No | Yes | Archive |
| `docs/architecture/cortex_architecture_debt_register.md` | Architecture Debt Register | Superseded debt register superseded by open work register | `STALE` | No | No | Yes | Archive |
| `artifacts/release_candidates/v0.3.0-experimental-rc1/*` | v0.3.0-rc1 Release Evidence | Immutable release candidate evidence dossier | `HISTORICAL_RELEASE_EVIDENCE` | Yes | Yes | Yes | Immutable Retain |
