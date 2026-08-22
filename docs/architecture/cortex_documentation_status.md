# Cortex Documentation Status & Canonical Mapping Register
**Authoritative Documentation Governance Matrix**  
**Date:** August 22, 2026  
**Repository Baseline SHA:** `1927eb4` (`main`)

---

## 1. Documentation Canonical Status Table

| Document | Domain | Classification | Canonical? | Current? | Historical? | Referenced? | Action | Replacement / Canonical Target | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `README.md` | Core | `CANONICAL_ARCHITECTURE` | Yes | Yes | No | Yes | RETAIN | N/A | Primary system entrypoint |
| `docs/README.md` | Core | `CANONICAL_GOVERNANCE` | Yes | Yes | No | Yes | RETAIN | N/A | Master documentation index |
| `cortex_system_architecture_current.md` | Architecture | `CANONICAL_ARCHITECTURE` | Yes | Yes | No | Yes | RETAIN | N/A | Canonical current architecture spec |
| `configuration_and_control_plane_specification.md` | Architecture | `CANONICAL_SPECIFICATION` | Yes | Yes | No | Yes | RETAIN | N/A | Canonical configuration specification |
| `invocation_ledger_compaction_design.md` | Architecture | `CANONICAL_SPECIFICATION` | Yes | Yes | No | Yes | RETAIN | N/A | Canonical ledger compaction spec |
| `phase_4_routing_and_dispatch_specification.md` | Architecture | `CANONICAL_SPECIFICATION` | Yes | Yes | No | Yes | RETAIN | N/A | Canonical Phase 4 specification |
| `phase_5_load_balancing_specification.md` | Architecture | `CANONICAL_SPECIFICATION` | Yes | Yes | No | Yes | RETAIN | N/A | Canonical Phase 5 specification |
| `replica_scaling_specification.md` | Architecture | `CANONICAL_SPECIFICATION` | Yes | Yes | No | Yes | RETAIN | N/A | Canonical scaling & sandbox spec |
| `threat_model.md` | Security | `CANONICAL_ARCHITECTURE` | Yes | Yes | No | Yes | RETAIN | N/A | Canonical security threat model |
| `api-stability-policy.md` | Governance | `CANONICAL_GOVERNANCE` | Yes | Yes | No | Yes | RETAIN | N/A | Canonical API stability policy |
| `canonical-serialization.md` | Spec | `CANONICAL_SPECIFICATION` | Yes | Yes | No | Yes | RETAIN | N/A | Canonical CBE serialization spec |
| `code_quality_policy.md` | Governance | `CANONICAL_GOVERNANCE` | Yes | Yes | No | Yes | RETAIN | N/A | Canonical code quality policy |
| `commit_quality_policy.md` | Governance | `CANONICAL_GOVERNANCE` | Yes | Yes | No | Yes | RETAIN | N/A | Canonical git commit policy |
| `contributor_security_boundaries.md` | Security | `CANONICAL_GOVERNANCE` | Yes | Yes | No | Yes | RETAIN | N/A | Canonical contributor boundary policy |
| `cortex_completed_work_register.md` | Ledger | `CANONICAL_ASSURANCE` | Yes | Yes | Historical | Yes | RETAIN | N/A | Canonical historical completion ledger |
| `cortex_open_work_register.md` | Backlog | `CANONICAL_ROADMAP` | Yes | Yes | No | Yes | RETAIN | N/A | Canonical open work backlog |
| `cortex_current_repository_inventory.md` | Inventory | `CANONICAL_OPERATIONAL` | Yes | Yes | No | Yes | RETAIN | N/A | Canonical physical asset inventory |
| `cortex_release_accounting_register.md` | Release | `CANONICAL_GOVERNANCE` | Yes | Yes | Historical | Yes | RETAIN | N/A | Canonical release registry |
| `cortex_github_full_state_audit.md` | Audit | `CANONICAL_ASSURANCE` | Yes | Yes | No | Yes | RETAIN | N/A | Canonical GitHub issue audit |
| `verification_closure_matrix.md` | Verification | `CANONICAL_ASSURANCE` | Yes | Yes | No | Yes | RETAIN | N/A | Canonical verification matrix |
| `cli_and_configuration_audit.md` | Architecture | `DUPLICATE` | No | No | Historical | Yes | ARCHIVE | `configuration_and_control_plane_specification.md` | Content merged into canonical spec |
| `configuration_standardization_audit.md` | Architecture | `DUPLICATE` | No | No | Historical | No | REMOVE | `configuration_and_control_plane_specification.md` | Content merged into canonical spec |
| `cortex_architecture_debt_register.md` | Architecture | `STALE` | No | No | Historical | Yes | ARCHIVE | `cortex_open_work_register.md` | Replaced by open work register |
| `cortex_future_implementation_plan.md` | Architecture | `STALE` | No | No | Historical | Yes | ARCHIVE | `cortex_open_work_register.md` | Replaced by open work register |
| `cortex_experimental_release_plan.md` | Architecture | `STALE` | No | No | Historical | Yes | ARCHIVE | `cortex_release_accounting_register.md` | Replaced by release register |
