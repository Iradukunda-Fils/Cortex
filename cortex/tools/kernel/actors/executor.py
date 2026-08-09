"""
TaskExecutor Actor

Consumes: PlanGeneratedEvent
Produces: CommandIssuedEvent

Iterates over the steps within a PlanGeneratedEvent and issues
individual CommandIssuedEvent instances to the driver layer.
The executor has zero knowledge of which driver will consume
the command — it only knows the message contract.
"""

from collections.abc import Callable
from typing import cast

from cortex.tools.kernel.context import RuntimeContext
from cortex.tools.kernel.schema.message import CommandIssuedEvent, PlanGeneratedEvent
from cortex.tools.kernel.transport import AnyEvent


class TaskExecutorActor:
    context: RuntimeContext
    publish_cb: Callable[[AnyEvent], object]

    def __init__(self, context: RuntimeContext, publish_cb: Callable[[AnyEvent], object]):
        self.context = context
        self.publish_cb = publish_cb

    def handle_plan(self, plan: PlanGeneratedEvent) -> list[CommandIssuedEvent]:
        commands: list[CommandIssuedEvent] = []
        for step in plan.steps:
            action_val = str(step.get("action", "unknown"))
            params_val = step.get("parameters", {})
            params_dict = cast(dict[str, object], params_val) if isinstance(params_val, dict) else {}

            cmd = CommandIssuedEvent(
                plan_id=plan.plan_id,
                correlation_id=plan.correlation_id,
                action=action_val,
                parameters=params_dict,
            )
            commands.append(cmd)
            self.publish_cb(cmd)
        return commands
