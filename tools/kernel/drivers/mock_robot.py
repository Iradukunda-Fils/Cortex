"""
Mock Robot Driver for Stage 2 Architecture Validation
"""

from tools.kernel.context import RuntimeContext
from tools.kernel.schema.event import MotorFeedbackEvent

class MockRobotDriver:
    def __init__(self, context: RuntimeContext, actuator_id: str = "arm_joint_1"):
        self.context = context
        self.actuator_id = actuator_id
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
        self.context.publish(event)
