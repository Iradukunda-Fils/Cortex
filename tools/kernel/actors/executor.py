"""
TaskExecutor Actor
"""

from typing import Callable, Any, List
from tools.kernel.context import RuntimeContext
from tools.kernel.schema.message import Plan, Command

class TaskExecutorActor:
    def __init__(self, context: RuntimeContext, publish_cb: Callable[[Any], None]):
        self.context = context
        self.publish_cb = publish_cb

    def handle_plan(self, plan: Plan) -> List[Command]:
        commands = []
        for step in plan.steps:
            cmd = Command(
                plan_id=plan.plan_id,
                correlation_id=plan.correlation_id,
                action=step.get("action", "unknown"),
                parameters=step.get("parameters", {})
            )
            commands.append(cmd)
            self.publish_cb(cmd)
        return commands
