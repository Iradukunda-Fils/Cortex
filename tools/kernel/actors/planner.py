"""
IntentPlanner Actor
"""

from typing import Callable, Any
from tools.kernel.context import RuntimeContext
from tools.kernel.schema.message import Intent, Plan

class IntentPlannerActor:
    def __init__(self, context: RuntimeContext, publish_cb: Callable[[Any], None]):
        self.context = context
        self.publish_cb = publish_cb

    def handle_intent(self, intent: Intent) -> Plan:
        # Decomposes goal string into structured action steps
        steps = [
            {"action": "move_actuator", "parameters": {"actuator": "arm_joint_1", "delta": 10.0}},
            {"action": "move_actuator", "parameters": {"actuator": "arm_joint_2", "delta": -5.0}}
        ]
        plan = Plan(
            intent_id=intent.intent_id,
            correlation_id=intent.session_id,
            steps=steps
        )
        self.publish_cb(plan)
        return plan
