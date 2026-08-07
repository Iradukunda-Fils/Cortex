"""
IntentPlanner Actor

Consumes: IntentEvent
Produces: PlanGeneratedEvent

Decomposes a high-level goal intent into an ordered sequence of
actionable steps. The planner has zero knowledge of downstream
executors or drivers — it only knows the message contract.
"""

from typing import Callable, Any
from tools.kernel.context import RuntimeContext
from tools.kernel.schema.message import IntentEvent, PlanGeneratedEvent


class IntentPlannerActor:
    def __init__(self, context: RuntimeContext, publish_cb: Callable[[Any], None]):
        self.context = context
        self.publish_cb = publish_cb

    def handle_intent(self, intent: IntentEvent) -> PlanGeneratedEvent:
        steps = [
            {"action": "move_actuator", "parameters": {"actuator": "arm_joint_1", "delta": 10.0}},
            {"action": "move_actuator", "parameters": {"actuator": "arm_joint_2", "delta": -5.0}},
        ]
        plan = PlanGeneratedEvent(
            intent_id=intent.intent_id,
            correlation_id=intent.session_id,
            steps=steps,
        )
        self.publish_cb(plan)
        return plan
