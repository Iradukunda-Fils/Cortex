"""
Configurable Repository Auditor Planner Plugin

Parameterized planner that generates N audit steps to simulate
controlled Cortex workloads of varying sizes. Uses only public Cortex SDK.

Note: This generates synthetic workloads to measure Cortex runtime overhead
(event propagation, EventStore, replay). It does NOT perform real repository analysis.
"""

from cortex import (
    BaseEvent,
    BasePlugin,
    IntentEvent,
    PlanGeneratedEvent,
    PluginManifest,
)
from cortex.compat import override

# Named constants for workload boundaries
MIN_STEP_COUNT = 1
MAX_STEP_COUNT = 10_000
DEFAULT_STEP_COUNT = 3

# Canonical audit action set — rotated for workloads exceeding 10 steps
AUDIT_ACTIONS = (
    "git_status_check",
    "syntax_check",
    "unit_test_check",
    "dependency_audit",
    "license_compliance_check",
    "security_vulnerability_scan",
    "code_coverage_analysis",
    "documentation_lint",
    "type_check",
    "integration_test_check",
)


class ConfigurablePlannerPlugin(BasePlugin):
    """Planner plugin that generates a configurable number of synthetic audit steps.

    This is used for controlled Cortex workload profiling, NOT real repository analysis.
    """

    step_count: int

    def __init__(self, step_count: int = DEFAULT_STEP_COUNT) -> None:
        if not isinstance(step_count, int) or step_count < MIN_STEP_COUNT:
            raise ValueError(f"step_count must be a positive integer >= {MIN_STEP_COUNT}, got {step_count}")
        if step_count > MAX_STEP_COUNT:
            raise ValueError(f"step_count must be <= {MAX_STEP_COUNT}, got {step_count}")

        manifest = PluginManifest(
            name=f"configurable-planner-{step_count}",
            version="0.1.0",
            description=f"Generates {step_count} synthetic audit steps for workload profiling",
            consumes_events=["IntentEvent"],
            produces_events=["PlanGeneratedEvent"],
            required_capabilities=["workflow.plan.create"],
        )
        super().__init__(manifest)
        self.step_count = step_count

    @override
    def on_event(self, event: BaseEvent) -> None:
        match event:
            case IntentEvent() if self.context and self.context.has_capability("workflow.plan.create"):
                steps: list[dict[str, object]] = []
                for i in range(self.step_count):
                    action = AUDIT_ACTIONS[i % len(AUDIT_ACTIONS)]
                    steps.append(
                        {
                            "step": i + 1,
                            "action": action,
                            "params": {"path": ".", "iteration": i},
                        }
                    )

                plan_event = PlanGeneratedEvent(
                    workflow_id=event.workflow_id,
                    intent_id=event.intent_id,
                    causation_id=event.event_id,
                    steps=steps,
                )
                self.context.publish(plan_event)

            case _:
                pass
