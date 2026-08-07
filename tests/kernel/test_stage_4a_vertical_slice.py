"""
Stage 4A Autonomous Vertical Slice Test Suite

Validates the full Intent → Plan → Command → Telemetry → Verification
pipeline using zero-knowledge actors communicating over InMemoryTransport.
"""

import unittest
from tools.kernel.transport import InMemoryTransport
from tools.kernel.context import RuntimeContext
from tools.kernel.schema.message import (
    IntentEvent,
    PlanGeneratedEvent,
    CommandIssuedEvent,
    DriverTelemetryEvent,
    VerificationResultEvent,
)
from tools.kernel.actors.planner import IntentPlannerActor
from tools.kernel.actors.executor import TaskExecutorActor
from tools.kernel.drivers.mock_robot import MockRobotDriver
from tools.kernel.services.verification import VerificationKernelService
from tools.kernel.services.graph_builder import ExecutionGraphBuilderService


class TestStage4AVerticalSlice(unittest.TestCase):
    def setUp(self):
        self.transport = InMemoryTransport()
        self.context = RuntimeContext("actor_stage4a", "sess_stage4a", self.transport)
        self.graph_builder = ExecutionGraphBuilderService()
        self.message_bus = []

    def _publish(self, msg):
        self.message_bus.append(msg)
        self.graph_builder.record_message(msg)

    def test_end_to_end_autonomous_flow(self):
        planner = IntentPlannerActor(self.context, self._publish)
        executor = TaskExecutorActor(self.context, self._publish)
        driver = MockRobotDriver(self.context, self._publish)
        verifier = VerificationKernelService(self.context, self._publish)

        # 1. Dispatch IntentEvent
        intent = IntentEvent(session_id="sess_4a", goal="Execute Maintenance Routine")
        self._publish(intent)

        # 2. Planner produces PlanGeneratedEvent
        plan = planner.handle_intent(intent)
        self.assertEqual(plan.intent_id, intent.intent_id)
        self.assertEqual(len(plan.steps), 2)

        # 3. Executor produces CommandIssuedEvents
        commands = executor.handle_plan(plan)
        self.assertEqual(len(commands), 2)

        # 4. Driver executes commands and produces DriverTelemetryEvents
        telemetries = [driver.handle_command(cmd) for cmd in commands]
        self.assertEqual(len(telemetries), 2)

        # 5. Verifier evaluates telemetry and produces VerificationResultEvents
        verifications = [verifier.handle_telemetry(t) for t in telemetries]
        self.assertEqual(len(verifications), 2)
        self.assertTrue(all(v.passed for v in verifications))

        # 6. Validate Execution Graph DAG & lineage reconstruction
        self.assertIn(intent.intent_id, self.graph_builder.graphs)
        graph = self.graph_builder.graphs[intent.intent_id]

        tree_str = graph.render_tree()
        self.assertIn("[Intent]", tree_str)
        self.assertIn("[Plan]", tree_str)
        self.assertIn("[Command]", tree_str)
        self.assertIn("[Telemetry]", tree_str)
        self.assertIn("[Verification]", tree_str)

        # 1 Intent + 1 Plan + 2 Commands + 2 Telemetries + 2 Verifications = 8
        self.assertEqual(len(graph.nodes), 8)
        print("\n--- STAGE 4A CAUSAL EXECUTION GRAPH ---")
        print(tree_str)


if __name__ == "__main__":
    unittest.main()
