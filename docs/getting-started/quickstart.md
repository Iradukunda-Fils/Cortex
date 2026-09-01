# Cortex 5-Minute Developer Quickstart Guide

Get up and running with Cortex in under 5 minutes. This guide walks you through building a complete Python application with custom capability-gated plugins, executing a workflow, inspecting the event journal, and running deterministic trace replay—using **only** the public Cortex SDK.

---

## 📦 1. Installation

Install `cortex-runtime` via PyPI or using Astral `uv`:

```bash
# Standard pip
pip install cortex-runtime

# Fast installation with Astral uv
uv add cortex-runtime
```

Requirements: **Python 3.10+** (Python 3.10 through 3.14 fully supported).

---

## ⚡ 2. The 5-Minute Concept

In Cortex, application execution follows four steps:

```
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │ 1. Define    │ ──> │ 2. Register  │ ──> │ 3. Run       │ ──> │ 4. Inspect & │
  │    Plugins   │     │    Plugins   │     │    Workflow  │     │    Replay    │
  └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

1. **Define Plugins**: Create custom `BasePlugin` classes with declarative `PluginManifest` manifests.
2. **Register Plugins**: Attach plugins to `CortexClient`. The client negotiates capabilities statically.
3. **Run Workflow**: Start a `Workflow` lifecycle and publish an initiating `IntentEvent`.
4. **Inspect & Replay**: Access the immutable `EventStore` journal and run deterministic trace replay.

---

## 🚀 3. Complete Working Example Script

Create a file named `quickstart_demo.py` and paste the following code:

```python
"""
Cortex 5-Minute Quickstart Demonstration
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
    WorkflowState,
)
from cortex.compat import override

# --- Step 1: Define Plugin Manifests ---

PLANNER_MANIFEST = PluginManifest(
    name="quickstart-planner",
    version="0.1.0",
    description="Decomposes intent into actionable steps",
    consumes_events=["IntentEvent"],
    produces_events=["PlanGeneratedEvent"],
    required_capabilities=["workflow.plan.create"],
)

EXECUTOR_MANIFEST = PluginManifest(
    name="quickstart-executor",
    version="0.1.0",
    description="Executes planned steps with capability guardrails",
    consumes_events=["PlanGeneratedEvent"],
    produces_events=["DriverTelemetryEvent", "VerificationResultEvent"],
    required_capabilities=["fs.read"],
)

# --- Step 2: Implement Plugin Logic ---

class QuickstartPlanner(BasePlugin):
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
                    steps=[{"step": 1, "action": "check_workspace", "target": "."}],
                )
                self.context.publish(plan)
            case _:
                pass


class QuickstartExecutor(BasePlugin):
    def __init__(self) -> None:
        super().__init__(EXECUTOR_MANIFEST)

    @override
    def on_event(self, event: BaseEvent) -> None:
        match event:
            case PlanGeneratedEvent() if self.context and self.context.has_capability("fs.read"):
                for step in event.steps:
                    telemetry = DriverTelemetryEvent(
                        workflow_id=event.workflow_id,
                        causation_id=event.event_id,
                        driver_id="quickstart_driver",
                        status="ok",
                        payload=step,
                    )
                    self.context.publish(telemetry)

                    verification = VerificationResultEvent(
                        workflow_id=event.workflow_id,
                        causation_id=event.event_id,
                        passed=True,
                        rule_id="QUICKSTART_PASS",
                        details={"target": step.get("target")},
                    )
                    self.context.publish(verification)
            case _:
                pass

# --- Step 3: Orchestrate & Execute ---

def main() -> None:
    print("1. Initializing CortexClient...")
    client = CortexClient()

    print("2. Registering Plugins...")
    client.register_plugin(QuickstartPlanner())
    client.register_plugin(QuickstartExecutor())

    print("3. Creating & Running Workflow...")
    wf = client.create_workflow(name="QuickstartWorkflow", goal="Demonstrate Cortex SDK")
    intent = IntentEvent(workflow_id=wf.workflow_id, goal="Verify Workspace")
    executed_wf = client.run_workflow(wf, initial_intent=intent)

    print(f"\n[✓] Workflow Completed! Final State: {executed_wf.state.value}")
    assert executed_wf.state == WorkflowState.COMPLETED

    # --- Step 4: Inspect Event Log & Replay ---
    print("\n4. Inspecting Event Journal (EventStore):")
    log = client.event_store.get_log()
    for e in log:
        print(f"    - [{type(e).__name__}] ID: {e.event_id[:8]} | Cause: {str(e.causation_id)[:8]}")

    print("\n5. Saving & Replaying Execution Trace...")
    trace_path = client.save_trace(executed_wf.workflow_id, "/tmp/quickstart_trace.json")
    replay = client.replay_workflow(trace_path)
    print(f"    Replayed Events: {replay['replayed_count']}")
    print(f"    Deterministic Parity: {replay['deterministic']}")


if __name__ == "__main__":
    main()
```

---

## 🏃 4. Run the Quickstart Script

Run the script directly with Python:

```bash
python quickstart_demo.py
```

Expected Output:

```text
1. Initializing CortexClient...
2. Registering Plugins...
3. Starting Workflow...
4. Triggering Intent Event...

[✓] Workflow Completed! Final State: COMPLETED

5. Inspecting Event Journal (EventStore):
    - [IntentEvent] ID: e1a2b3c4 | Cause: None
    - [PlanGeneratedEvent] ID: f5g6h7i8 | Cause: e1a2b3c4
    - [DriverTelemetryEvent] ID: j9k0l1m2 | Cause: f5g6h7i8
    - [VerificationResultEvent] ID: n3o4p5q6 | Cause: f5g6h7i8

6. Saving & Replaying Execution Trace...
    Replayed Events: 4
    Deterministic Parity: True
```

---

## 📖 5. Next Steps

Now that you've run your first Cortex application:

- **Build Advanced Plugins**: Read the [Plugin Authoring Guide](guides/plugin-authoring.md) to learn about granular capability controls, security violation handling, and event lineage tracking.
- **Understand Architecture**: Explore the [Architecture Overview](architecture/overview.md) for a deep dive into the 3-Layer Security Boundary.
- **Check API Stability**: Review the [API Stability Policy](architecture/api-stability-policy.md) for SemVer guarantees.
- **Set Up Contributor Environment**: Follow the [Developer Setup Guide](development/setup.md) to contribute to Cortex.
