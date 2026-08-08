"""
Repository Auditor Planner Plugin

Decomposes IntentEvent into structured repository audit steps.
"""

from typing import override
from cortex import BaseEvent, BasePlugin, IntentEvent, PlanGeneratedEvent, PluginManifest

PLANNER_MANIFEST = PluginManifest(
    name="auditor-planner",
    version="0.1.0",
    description="Decomposes repository audit intents into step-wise execution plans",
    consumes_events=["IntentEvent"],
    produces_events=["PlanGeneratedEvent"],
    required_capabilities=["workflow.plan.create"],
)


class AuditorPlannerPlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__(PLANNER_MANIFEST)

    @override
    def on_event(self, event: BaseEvent) -> None:
        match event:
            case IntentEvent() if self.context and self.context.has_capability("workflow.plan.create"):
                audit_steps: list[dict[str, object]] = [
                    {"step": 1, "action": "git_status_check", "params": {"path": "."}},
                    {"step": 2, "action": "syntax_check", "params": {"path": "."}},
                    {"step": 3, "action": "unit_test_check", "params": {"suite": "tests"}},
                ]

                plan_event = PlanGeneratedEvent(
                    workflow_id=event.workflow_id,
                    intent_id=event.intent_id,
                    causation_id=event.event_id,
                    steps=audit_steps,
                )
                self.context.publish(plan_event)

            case _:
                pass
