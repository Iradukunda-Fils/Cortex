"""
Mock Robot Driver

Consumes: CommandIssuedEvent
Produces: DriverTelemetryEvent

Translates abstract commands into simulated actuator state changes
and emits raw telemetry facts. The driver has zero knowledge of
upstream planners or downstream verification services.

Also provides a legacy step_actuator() method for Stage 2
verification domain tests that operate through the event.py
MotorFeedbackEvent hierarchy.
"""

from typing import Callable, cast
from cortex.tools.kernel.context import RuntimeContext
from cortex.tools.kernel.schema.event import MotorFeedbackEvent
from cortex.tools.kernel.schema.message import CommandIssuedEvent, DriverTelemetryEvent
from cortex.tools.kernel.transport import AnyEvent


class MockRobotDriver:
    context: RuntimeContext
    actuator_id: str
    publish_cb: Callable[[AnyEvent], object]
    positions: dict[str, float]
    position: float
    velocity: float

    def __init__(
        self,
        context: RuntimeContext,
        actuator_id_or_cb: str | Callable[[AnyEvent], object] = "arm_joint_1",
        publish_cb: Callable[[AnyEvent], object] | None = None,
    ):
        self.context = context
        if callable(actuator_id_or_cb):
            self.actuator_id = "arm_joint_1"
            self.publish_cb = actuator_id_or_cb
        else:
            self.actuator_id = str(actuator_id_or_cb)
            self.publish_cb = publish_cb or context.publish

        self.positions = {"arm_joint_1": 0.0, "arm_joint_2": 0.0}
        self.position = 0.0
        self.velocity = 0.0

    # -- Verification Domain (event.py hierarchy) --------------------------

    def step_actuator(self, delta_pos: float, velocity: float) -> None:
        """Stage 2 verification interface emitting MotorFeedbackEvent."""
        self.position += delta_pos
        self.velocity = velocity
        event = MotorFeedbackEvent(
            session_id=self.context.session_id,
            actuator_id=self.actuator_id,
            position=self.position,
            velocity=self.velocity,
        )
        _ = self.publish_cb(event)

    # -- Kernel Runtime Domain (message.py hierarchy) ----------------------

    def handle_command(self, cmd: CommandIssuedEvent) -> DriverTelemetryEvent:
        """Stage 4 kernel interface consuming CommandIssuedEvent."""
        actuator = cast(str, cmd.parameters.get("actuator", "arm_joint_1"))
        delta = float(cast(int | float, cmd.parameters.get("delta", 0.0)))

        current = self.positions.get(actuator, 0.0) + delta
        self.positions[actuator] = current

        telemetry = DriverTelemetryEvent(
            causation_id=cmd.command_id,
            correlation_id=cmd.correlation_id,
            root_id=cmd.plan_id,
            driver_id=actuator,
            status="ok",
            payload={"actuator": actuator, "position": current, "delta": delta},
        )
        _ = self.publish_cb(telemetry)
        return telemetry
