"""
TaskExecutor Actor

Consumes: PlanGeneratedEvent
Produces: CommandIssuedEvent

Iterates over the steps within a PlanGeneratedEvent and issues
individual CommandIssuedEvent instances to the driver layer.
The executor has zero knowledge of which driver will consume
the command — it only knows the message contract.
"""

from typing import Callable, Any, List
from tools.kernel.context import RuntimeContext
from tools.kernel.schema.message import PlanGeneratedEvent, CommandIssuedEvent


class TaskExecutorActor:
    def __init__(self, context: RuntimeContext, publish_cb: Callable[[Any], None]):
        self.context = context
        self.publish_cb = publish_cb

    def handle_plan(self, plan: PlanGeneratedEvent) -> List[CommandIssuedEvent]:
        commands: List[CommandIssuedEvent] = []
        for step in plan.steps:
            cmd = CommandIssuedEvent(
                plan_id=plan.plan_id,
                correlation_id=plan.correlation_id,
                action=step.get("action", "unknown"),
                parameters=step.get("parameters", {}),
            )
            commands.append(cmd)
            self.publish_cb(cmd)
        return commands
