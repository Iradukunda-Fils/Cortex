# Cortex API Stability Policy

> **Version**: 1.0.0
> **Applies to**: Cortex v0.2.x and forward
> **Last updated**: 2026-08-10

---

## 1. Purpose

This document defines the public API boundary of the Cortex SDK, the stability
guarantees offered to external consumers, and the deprecation lifecycle that governs
changes to the supported interface.

External applications, plugins, and tools SHOULD depend exclusively on the symbols
documented here as **Public**. Symbols not listed as Public are considered **Internal**
and may change without notice in any release.

---

## 2. Semantic Versioning (SemVer 2.0.0)

Cortex follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html):

- **MAJOR** (e.g., 1.0.0 → 2.0.0): Backward-incompatible changes to the public API.
- **MINOR** (e.g., 0.2.0 → 0.3.0): New features added in a backward-compatible manner.
- **PATCH** (e.g., 0.2.0 → 0.2.1): Backward-compatible bug fixes.

### Pre-1.0 Stability Rules (Current)

While Cortex is pre-1.0 (i.e., `0.x.y`):

- **MINOR** version bumps (e.g., 0.2 → 0.3) MAY include breaking changes to the
  public API, but only with explicit documentation in the changelog and at least
  one PATCH release with deprecation warnings.
- **PATCH** version bumps (e.g., 0.2.0 → 0.2.1) MUST NOT introduce breaking changes
  to the public API.
- The public symbol set frozen in `cortex.__all__` MUST remain stable within a
  MINOR version series (e.g., all 0.2.x releases share the same public boundary).

### Post-1.0 Stability Rules (Future)

After Cortex 1.0.0:

- **MAJOR** bumps are the only mechanism for removing or renaming public symbols.
- **MINOR** bumps may add new public symbols but MUST NOT remove existing ones.
- **PATCH** bumps MUST NOT alter the public API surface in any way.

---

## 3. Public vs. Internal Classification

### 3.1 Public Symbols

Public symbols are those explicitly listed in `cortex/__init__.py`'s `__all__` list.
As of v0.2.x, the public API surface consists of **21 symbols**:

#### Core Client
| Symbol | Type | Description |
|:--|:--|:--|
| `CortexClient` | Class | Primary entry point for workflow orchestration |
| `EventStore` | Class | Append-only event journal (re-exported alias) |

#### Plugin System
| Symbol | Type | Description |
|:--|:--|:--|
| `BasePlugin` | ABC | Abstract base class for all plugins |
| `PluginManifest` | Dataclass | Plugin metadata and capability declaration |
| `PluginContext` | Class | Runtime context provided to active plugins |
| `Capability` | Dataclass | Named capability for sandboxed negotiation |

#### Event Schema
| Symbol | Type | Description |
|:--|:--|:--|
| `BaseEvent` | Dataclass | Immutable base event with causal lineage fields |
| `IntentEvent` | Dataclass | Workflow intent declaration |
| `PlanGeneratedEvent` | Dataclass | Plan generation output |
| `CommandIssuedEvent` | Dataclass | Execution command |
| `DriverTelemetryEvent` | Dataclass | Runtime telemetry observation |
| `TelemetryEvent` | Dataclass | Generic telemetry event |
| `VerificationResultEvent` | Dataclass | Verification pass/fail result |

#### Workflow Types
| Symbol | Type | Description |
|:--|:--|:--|
| `Workflow` | Dataclass | First-class execution unit |
| `WorkflowState` | Enum | Lifecycle states: PENDING → RUNNING → COMPLETED/FAILED/ABORTED |
| `WorkflowPolicy` | Dataclass | Execution policy (timeout, retries, abort behavior) |

#### Exceptions
| Symbol | Type | Description |
|:--|:--|:--|
| `CortexError` | Exception | Base exception (exit code 1) |
| `WorkflowExecutionError` | Exception | Workflow runtime failure (exit code 1) |
| `CapabilityViolationError` | Exception | Unauthorized capability access (exit code 2) |
| `ManifestError` | Exception | Invalid plugin manifest (exit code 3) |

#### Compatibility
| Symbol | Type | Description |
|:--|:--|:--|
| `override` | Decorator | Python < 3.12 compatibility shim for `typing.override` |

### 3.2 Supported Import Paths

External consumers SHOULD use only these import patterns:

```python
# Direct import from cortex package (recommended)
from cortex import CortexClient, BasePlugin, IntentEvent

# Compatibility shim
from cortex import override
# or equivalently:
from cortex.compat import override

# Schema types
from cortex import BaseEvent, Workflow, WorkflowState
```

### 3.3 Internal Symbols

Everything not listed in `cortex.__all__` is considered **internal** and **unsupported**.
Internal modules include but are not limited to:

| Module Path | Classification | Stability |
|:--|:--|:--|
| `cortex.tools.*` | Internal | No guarantees |
| `cortex.tools.kernel.*` | Internal | No guarantees |
| `cortex.tools.kernel.actors.*` | Internal | No guarantees |
| `cortex.tools.kernel.services.*` | Internal | No guarantees |
| `cortex.tools.kernel.plugin.*` | Internal | No guarantees |
| `cortex.tools.kernel.transport.*` | Internal | No guarantees |
| `cortex.tools.kernel.graph.*` | Internal | No guarantees |
| `cortex.tools.verification.*` | Internal | No guarantees |

> **Warning**: Importing from internal modules directly (e.g.,
> `from cortex.tools.kernel.services.event_store import EventStoreService`)
> will work at the Python level but is explicitly **unsupported**. These paths
> may change, be renamed, or be removed in any release without notice.

### 3.4 Wildcard Import Protection

All internal subpackages define `__all__ = []` to prevent `from cortex.tools.kernel import *`
from leaking internal symbols into consuming namespaces. This is enforced by the regression
test suite (`test_v020_public_api_surface.py`).

---

## 4. Deprecation Lifecycle

When a public symbol must be changed or removed, the following lifecycle applies:

### Phase 1: Deprecation Warning (minimum 1 MINOR release)

- The symbol continues to function normally.
- A `DeprecationWarning` is emitted on first use.
- The warning message MUST include:
  - What is deprecated
  - What to use instead
  - The version in which removal is planned
- Documentation is updated to mark the symbol as deprecated.

```python
import warnings

def deprecated_function():
    warnings.warn(
        "deprecated_function() is deprecated and will be removed in v0.4.0. "
        "Use new_function() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return new_function()
```

### Phase 2: Removal (MAJOR bump, or MINOR bump pre-1.0)

- The symbol is removed from `cortex.__all__` and the import path.
- The removal is documented in the changelog with migration instructions.
- The regression test suite is updated to reflect the new symbol set.

### Grace Period

| Cortex Version | Minimum Deprecation Period |
|:--|:--|
| Pre-1.0 (0.x.y) | 1 MINOR release (e.g., deprecated in 0.2.x, removed in 0.3.0) |
| Post-1.0 (≥1.0.0) | 2 MINOR releases minimum |

---

## 5. Exception Contract Stability

Exit codes associated with exception types are part of the public API contract:

| Exception | Exit Code | Stability |
|:--|:--|:--|
| `CortexError` | 1 | Stable (v0.2+) |
| `WorkflowExecutionError` | 1 | Stable (v0.2+) |
| `CapabilityViolationError` | 2 | Stable (v0.2+) |
| `ManifestError` | 3 | Stable (v0.2+) |

Exit codes MUST NOT change within a MINOR version series. New exception types
added in future versions MUST receive exit codes ≥ 4.

---

## 6. Return Value & Behavioral Contracts

### 6.1 Event Immutability

All event types (`BaseEvent` and subclasses) are **frozen dataclasses**. This guarantee
is part of the public API:
- Events cannot be modified after creation.
- Event fields are typed and validated at construction time.
- The causal lineage fields (`event_id`, `workflow_id`, `causation_id`, `correlation_id`,
  `root_id`, `timestamp_ns`) are present on all events.

### 6.2 Replay Determinism

The `CortexClient.replay_workflow()` method guarantees **deterministic replay** for
any trace produced by `CortexClient.save_trace()`:
- Given the same trace file, replay MUST produce the same event sequence.
- Event lineage relationships MUST be preserved exactly.

### 6.3 Capability Enforcement

The capability negotiation system guarantees:
- Plugins cannot execute operations for capabilities they were not granted.
- Unauthorized capability access raises `CapabilityViolationError`.
- The `PluginManifest.required_capabilities` declaration is the single source of truth.

---

## 7. Compatibility Guarantees

### 7.1 Python Version Support

| Cortex Version | Minimum Python | Maximum Python |
|:--|:--|:--|
| v0.2.x | 3.10 | Latest stable |

The `cortex.compat` module provides the `override` decorator for Python versions
that do not include `typing.override` (pre-3.12).

### 7.2 Dependency Stability

Runtime dependencies declared in `pyproject.toml` are part of the operational contract.
New runtime dependencies MUST NOT be added in PATCH releases. New runtime dependencies
in MINOR releases must be justified and documented.

---

## 8. Regression Enforcement

The public API surface is continuously validated by the regression test suite:

- **`tests/regression/test_v020_public_api_surface.py`**: Freezes the exact symbol set,
  validates types, docstrings, and boundary enforcement.
- **`tests/regression/test_v020_event_lineage.py`**: Validates causal lineage contracts.
- **`tests/regression/test_v020_event_serialization.py`**: Validates JSON round-trip stability.
- **`tests/regression/test_v020_cli_contract.py`**: Validates CLI exit codes and error output.

Any change to `cortex/__init__.py` or `cortex.__all__` MUST update the corresponding
regression test or the CI pipeline will fail.
