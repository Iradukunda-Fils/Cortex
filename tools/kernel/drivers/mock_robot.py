"""
Mock Robot Driver for Stage 2 & Stage 4A Autonomous Execution
"""

from typing import Callable, Any, Optional
from tools.kernel.context import RuntimeContext
from tools.kernel.schema.event import MotorFeedbackEvent
from tools.kernel.schema.message import Command, DriverTelemetryEvent

class MockRobotDriver:
    def __init__(
        self,
        context: RuntimeContext,
        actuator_id_or_cb: Any = "arm_joint_1",
        publish_cb: Optional[Callable[[Any], None]] = None
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

    def step_actuator(self, delta_pos: float, velocity: float) -> None:
        self.position += delta_pos
        self.velocity = velocity
        event = MotorFeedbackEvent(
            session_id=self.context.session_id,
            actuator_id=self.actuator_id,
            position=self.position,
            velocity=self.velocity
        )
        self.publish_cb(event)

    def handle_command(self, cmd: Command) -> DriverTelemetryEvent:
        actuator = cmd.parameters.get("actuator", "arm_joint_1")
        delta = cmd.parameters.get("delta", 0.0)

        current = self.positions.get(actuator, 0.0) + delta
        self.positions[actuator] = current

        telemetry = DriverTelemetryEvent(
            causation_id=cmd.command_id,
            correlation_id=cmd.correlation_id,
            root_id=cmd.plan_id,
            status="ok",
            payload={"actuator": actuator, "position": current, "delta": delta}
        )
        self.publish_cb(telemetry)
        return telemetry
