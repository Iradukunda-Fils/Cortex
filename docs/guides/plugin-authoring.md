# Building Plugins for Cortex: Complete Authoring Guide

> **Target Audience**: Developers creating autonomous software components, AI agent extensions, and domain event processors for the Cortex platform.
> **SDK Version**: `cortex-runtime >= 0.3.0`
> **Public API Imports**: All examples in this guide import exclusively from the public `cortex` namespace.

---

## 1. Introduction & Security Boundary Model

Cortex operates on a **sandboxed capability model**. Unlike traditional plugin systems where plugins run with full ambient permissions of the host process, Cortex requires plugins to:

1. **Declare explicit capabilities** upfront in a `PluginManifest`.
2. **Undergo static negotiation** when registering with the `CortexClient`.
3. **Assert permissions at runtime** before executing guarded operations (`self.context.has_capability(...)`).

If a plugin attempts an action for which it lacks an authorized capability, the platform intercepts the action, records a `CAPABILITY_VIOLATION` event, and transitions the workflow state to `FAILED`.

```
┌────────────────────────────────────────────────────────────────────────┐
│                              CORTEX KERNEL                             │
│                                                                        │
│   ┌──────────────────┐           ┌────────────────────────────────┐   │
│   │  PluginManifest  │ ────────> │ static capability negotiation  │   │
│   └──────────────────┘           └────────────────────────────────┘   │
│                                                   │                    │
│                                                   ▼                    │
│   ┌──────────────────┐           ┌────────────────────────────────┐   │
│   │   on_event()     │ ────────> │ self.context.has_capability()  │   │
│   └──────────────────┘           └────────────────────────────────┘   │
│                                                   │                    │
│                                          ┌────────┴────────┐           │
│                                          ▼                 ▼           │
│                                      [GRANTED]        [VIOLATION]      │
│                                          │                 │           │
│                                          ▼                 ▼           │
│                                      Publish         EventStore Log    │
│                                       Event         WorkflowState.FAILED│
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Abstractions

All plugin development relies on five public symbols exported directly by `cortex`:

```python
from cortex import (
    BaseEvent,
    BasePlugin,
    Capability,
    PluginContext,
    PluginManifest,
)
from cortex.compat import override
```

### Key Components

| Component | Type | Responsibility |
|:--|:--|:--|
| `PluginManifest` | Dataclass | Metadata, consumed events, produced events, and required capability tokens. |
| `BasePlugin` | ABC | Base class that plugin implementations inherit from. |
| `PluginContext` | Class | Host interface passed to active plugins. Provides `.has_capability()` and `.publish()`. |
| `Capability` | Dataclass | Immutable token representing a specific privilege (e.g., `fs:read`, `exec:git`). |
| `override` | Decorator | Cross-version decorator compatibility shim for Python < 3.12. |

---

## 3. The 5-Step Plugin Lifecycle

Developing a Cortex plugin follows five canonical steps:

### Step 1: Declare the `PluginManifest`

Define your plugin's identity, input events, output events, and required capabilities:

```python
from cortex import PluginManifest

AUDITOR_MANIFEST = PluginManifest(
    name="repository-hygiene-auditor",
    version="0.1.0",
    description="Analyzes repository structure and publishes audit findings",
    consumes_events=["IntentEvent", "CommandIssuedEvent"],
    produces_events=["DriverTelemetryEvent", "VerificationResultEvent"],
    required_capabilities=["fs:read", "exec:git"],
)
```

### Step 2: Inherit from `BasePlugin`

Pass the manifest to `super().__init__()`:

```python
from cortex import BasePlugin

class RepositoryHygienePlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__(AUDITOR_MANIFEST)
```

### Step 3: Implement `on_event(event)` with Pattern Matching

Cortex dispatches domain events to active plugins via `on_event()`. Use Python 3.10+ `match/case` to handle relevant event types:

```python
from cortex import BaseEvent, CommandIssuedEvent
from cortex.compat import override

class RepositoryHygienePlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__(AUDITOR_MANIFEST)

    @override
    def on_event(self, event: BaseEvent) -> None:
        match event:
            case CommandIssuedEvent():
                self._handle_command(event)
            case _:
                pass
```

### Step 4: Assert Capability Authorization

Before executing any privilege-sensitive operation or emitting results, verify authorization using `self.context.has_capability()`:

```python
    def _handle_command(self, event: CommandIssuedEvent) -> None:
        if not self.context:
            return

        # Check permission boundary
        if not self.context.has_capability("fs:read"):
            return  # Permission denied by sandbox policy
```

### Step 5: Publish Downstream Events with Causal Lineage

Construct downstream events and assign `causation_id` to `event.event_id` to preserve causal lineage in the `EventStore`:

```python
from cortex import DriverTelemetryEvent, VerificationResultEvent

        # 1. Publish runtime telemetry
        telemetry = DriverTelemetryEvent(
            workflow_id=event.workflow_id,
            causation_id=event.event_id,  # Causal parent link
            driver_id="fs_reader",
            status="ok",
            payload={"action": event.action, "path": "."},
        )
        self.context.publish(telemetry)

        # 2. Publish verification result
        result = VerificationResultEvent(
            workflow_id=event.workflow_id,
            causation_id=event.event_id,
            passed=True,
            rule_id="HYGIENE_CHECK_PASSED",
            details={"scanned_files": 42},
        )
        self.context.publish(result)
```

---

## 4. Causal Event Lineage & Event Store

Every event in Cortex inherits from `BaseEvent` and carries causal tracking fields:

| Field | Type | Description |
|:--|:--|:--|
| `event_id` | `str` | Unique UUID assigned at event creation. |
| `workflow_id` | `str` | UUID of the executing workflow lifecycle. |
| `causation_id` | `str \| None` | `event_id` of the direct cause/trigger event. |
| `correlation_id` | `str \| None` | Shared correlation ID across related operations. |
| `root_id` | `str \| None` | Root `event_id` that initiated the entire chain. |
| `timestamp_ns` | `int` | Nanosecond UTC timestamp. |

### Inspecting the Event Log

Host applications access the append-only event journal via `cortex.EventStore`:

```python
from cortex import CortexClient

client = CortexClient()
# ... register plugins and run workflow ...

# Retrieve the event log
log = client.event_store.get_log()

for event in log:
    print(f"[{event.timestamp_ns}] {type(event).__name__} | ID: {event.event_id[:8]} | Cause: {str(event.causation_id)[:8]}")
```

---

## 5. Handling Security Violations

When a plugin attempts an operation for which it did not declare capability in its `PluginManifest`, or when `has_capability()` returns `False`:

```python
class RoguePlugin(BasePlugin):
    @override
    def on_event(self, event: BaseEvent) -> None:
        match event:
            case CommandIssuedEvent() if self.context:
                # Attempting unauthorized write capability
                if not self.context.has_capability("fs:write"):
                    # Emit a verification failure event
                    failure = VerificationResultEvent(
                        workflow_id=event.workflow_id,
                        causation_id=event.event_id,
                        passed=False,
                        rule_id="CAPABILITY_VIOLATION",
                        details={"required": "fs:write", "status": "DENIED"},
                    )
                    self.context.publish(failure)
```

When a `VerificationResultEvent` with `passed=False` or a `CapabilityViolationError` is raised, the Cortex engine updates the workflow state to `WorkflowState.FAILED`.

---

## 6. Complete End-to-End Working Example

Below is a self-contained, copy-pasteable Python script building two cooperating plugins using **only** public `cortex.*` symbols:

```python
"""
Complete Cortex Plugin Authoring Demonstration

Demonstrates:
1. PlannerPlugin: Consumes IntentEvent -> Produces PlanGeneratedEvent
2. ExecutorPlugin: Consumes PlanGeneratedEvent -> Produces DriverTelemetryEvent & VerificationResultEvent
3. CortexClient workflow execution & event log inspection
"""

from cortex import (
    BaseEvent,
    BasePlugin,
    CommandIssuedEvent,
    CortexClient,
    DriverTelemetryEvent,
    IntentEvent,
    PlanGeneratedEvent,
    PluginManifest,
    VerificationResultEvent,
    Workflow,
    WorkflowPolicy,
    WorkflowState,
)
from cortex.compat import override

# --- 1. Manifest Declarations ---

PLANNER_MANIFEST = PluginManifest(
    name="demo-planner",
    version="1.0.0",
    description="Decomposes intent into execution steps",
    consumes_events=["IntentEvent"],
    produces_events=["PlanGeneratedEvent"],
    required_capabilities=["workflow.plan.create"],
)

EXECUTOR_MANIFEST = PluginManifest(
    name="demo-executor",
    version="1.0.0",
    description="Executes planned steps",
    consumes_events=["PlanGeneratedEvent"],
    produces_events=["DriverTelemetryEvent", "VerificationResultEvent"],
    required_capabilities=["fs:read"],
)

# --- 2. Plugin Implementations ---

class DemoPlannerPlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__(PLANNER_MANIFEST)

    @override
    def on_event(self, event: BaseEvent) -> None:
        match event:
            case IntentEvent() if self.context and self.context.has_capability("workflow.plan.create"):
                plan = PlanGeneratedEvent(
                    workflow_id=event.workflow_id,
                    intent_id=event.intent_id,
                    causation_id=event.event_id,
                    steps=[
                        {"step": 1, "action": "inspect_directory", "target": "."},
                    ],
                )
                self.context.publish(plan)
            case _:
                pass


class DemoExecutorPlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__(EXECUTOR_MANIFEST)

    @override
    def on_event(self, event: BaseEvent) -> None:
        match event:
            case PlanGeneratedEvent() if self.context and self.context.has_capability("fs:read"):
                for step in event.steps:
                    telemetry = DriverTelemetryEvent(
                        workflow_id=event.workflow_id,
                        causation_id=event.event_id,
                        driver_id="demo_executor",
                        status="ok",
                        payload=step,
                    )
                    self.context.publish(telemetry)

                    result = VerificationResultEvent(
                        workflow_id=event.workflow_id,
                        causation_id=event.event_id,
                        passed=True,
                        rule_id="STEP_EXECUTION_SUCCESS",
                        details={"action": step.get("action")},
                    )
                    self.context.publish(result)
            case _:
                pass

# --- 3. Main Execution Orchestrator ---

def main() -> None:
    client = CortexClient()
    client.register_plugin(DemoPlannerPlugin())
    client.register_plugin(DemoExecutorPlugin())

    wf = client.create_workflow(name="PluginDemo", goal="Verify custom plugins")
    intent = IntentEvent(workflow_id=wf.workflow_id, goal="Inspect codebase")
    executed_wf = client.run_workflow(wf, initial_intent=intent)

    print(f"Workflow State: {executed_wf.state.value}")
    assert executed_wf.state == WorkflowState.COMPLETED

    log = client.event_store.get_log()
    print(f"Total Recorded Events: {len(log)}")
    for e in log:
        print(f"  - [{type(e).__name__}] ID: {e.event_id[:8]} Cause: {str(e.causation_id)[:8]}")


if __name__ == "__main__":
    main()
```
