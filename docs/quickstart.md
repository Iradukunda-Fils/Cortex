# Cortex Developer Quickstart Guide

This guide walks you through creating your first Cortex application and custom plugin.

---

## Prerequisites & Installation

Cortex requires **Python 3.10+**. Install the package via PyPI:

```bash
pip install cortex-runtime
```

---

## 1. Scaffolding a New Project

Use the `cortex` CLI to initialize a new application workspace:

```bash
cortex init my_app --type app
cd my_app
```

This creates:
- `cortex.json`: Project manifest metadata.
- `manifest.json`: Plugin capability requirements.
- `workflow.json`: Declarative workflow specification.
- `main.py`: Application entrypoint.

---

## 2. Running a Workflow

Execute the workflow specification:

```bash
cortex workflow run workflow.json
```

Output:
```text
[+] Workflow execution finished.
    ID:          52279614-731b-4f16-8848-61feff398ece
    State:       COMPLETED
    Events Log:  1
    Trace Saved: .cortex/events/52279614-731b-4f16-8848-61feff398ece.json
```

---

## 3. Inspecting and Replaying Traces

Inspect the execution causality graph:

```bash
cortex workflow inspect .cortex/events/<workflow_id>.json
```

Replay trace events deterministically:

```bash
cortex workflow replay .cortex/events/<workflow_id>.json
```

---

## 4. Creating a Custom Plugin

```python
from cortex import BasePlugin, PluginManifest, IntentEvent, PlanGeneratedEvent

manifest = PluginManifest(
    name="my-custom-plugin",
    version="0.1.0",
    description="Custom planner plugin",
    consumes_events=["IntentEvent"],
    produces_events=["PlanGeneratedEvent"],
    required_capabilities=["workflow.plan.create"],
)

class MyPlannerPlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__(manifest)

    def on_event(self, event: object) -> None:
        if isinstance(event, IntentEvent) and self.context:
            plan = PlanGeneratedEvent(
                intent_id=event.intent_id,
                workflow_id=event.workflow_id,
                steps=[{"step": 1, "action": "analyze"}]
            )
            self.context.publish(plan)
```
