"""
Stage 4B Execution Graph Analysis, Intelligence & Deterministic Replay Test Suite
"""

import unittest
from tools.kernel.transport import InMemoryTransport
from tools.kernel.context import RuntimeContext
from tools.kernel.schema.message import Intent, Plan, Command, DriverTelemetryEvent, VerificationResultEvent, Event
from tools.kernel.schema.workflow import Workflow, WorkflowState, WorkflowPolicy
from tools.kernel.graph.analyzer import ExecutionGraphAnalyzer
from tools.kernel.services.execution_intelligence import CausalExplainer
from tools.kernel.services.replay import DeterministicReplayEngine
from tools.kernel.services.graph_builder import ExecutionGraphBuilderService

class TestStage4BAnalysisAndReplay(unittest.TestCase):
    def setUp(self):
        self.transport = InMemoryTransport()
        self.context = RuntimeContext("stage_4b_actor", "sess_4b", self.transport)
        self.graph_builder = ExecutionGraphBuilderService()

    def test_workflow_primitive_and_causal_explainer(self):
        # 1. Create Workflow Primitive
        wf = Workflow(
            name="verification_sweep_01",
            goal="Verify Actuator Limits",
            policy=WorkflowPolicy(abort_on_verification_failure=True)
        )
        self.assertEqual(wf.state, WorkflowState.PENDING)

        # 2. Build execution graph
        intent = Intent(session_id="sess_explain", goal=wf.goal)
        wf.root_intent_id = intent.intent_id
        wf.state = WorkflowState.RUNNING
        self.graph_builder.record_message(intent)

        plan = Plan(intent_id=intent.intent_id, steps=[{"action": "test_overdrive"}])
        self.graph_builder.record_message(plan)

        cmd = Command(plan_id=plan.plan_id, action="test_overdrive", parameters={"force": 200})
        self.graph_builder.record_message(cmd)

        telemetry = DriverTelemetryEvent(causation_id=cmd.command_id, status="error", payload={"force": 200})
        self.graph_builder.record_message(telemetry)

        verif_fail = VerificationResultEvent(
            causation_id=telemetry.event_id,
            passed=False,
            rule_id="TORQUE_LIMIT_SAFEGUARD"
        )
        self.graph_builder.record_message(verif_fail)

        graph = self.graph_builder.graphs[intent.intent_id]

        # 3. Test CausalExplainer
        explainer = CausalExplainer(graph)
        explanation = explainer.explain_failure(verif_fail.event_id)

        self.assertEqual(explanation["target_node"], verif_fail.event_id)
        self.assertIn("TORQUE_LIMIT_SAFEGUARD", explanation["diagnosis"])
        self.assertEqual(len(explanation["causal_path"]), 5)

        if wf.policy.abort_on_verification_failure:
            wf.state = WorkflowState.ABORTED

        self.assertEqual(wf.state, WorkflowState.ABORTED)

    def test_root_cause_analysis_and_graph_diff(self):
        intent = Intent(session_id="sess_rca", goal="Hazardous Calibration")
        self.graph_builder.record_message(intent)

        plan = Plan(intent_id=intent.intent_id, steps=[{"action": "overdrive_actuator"}])
        self.graph_builder.record_message(plan)

        cmd = Command(plan_id=plan.plan_id, action="overdrive_actuator", parameters={"power": 150})
        self.graph_builder.record_message(cmd)

        telemetry = DriverTelemetryEvent(causation_id=cmd.command_id, status="error", payload={"position": 150.0})
        self.graph_builder.record_message(telemetry)

        verif_fail = VerificationResultEvent(
            causation_id=telemetry.event_id,
            passed=False,
            rule_id="MAX_POWER_LIMIT_EXCEEDED"
        )
        self.graph_builder.record_message(verif_fail)

        graph = self.graph_builder.graphs[intent.intent_id]
        analyzer = ExecutionGraphAnalyzer(graph)

        failed_nodes = analyzer.find_failed_nodes()
        self.assertEqual(len(failed_nodes), 1)

        lineage_path = analyzer.find_root_cause(verif_fail.event_id)
        node_types = [n.node_type for n in lineage_path]
        self.assertEqual(node_types, ["Verification", "Telemetry", "Command", "Plan", "Intent"])

        diff = ExecutionGraphAnalyzer.diff_graphs(graph, graph)
        self.assertTrue(diff["identical_structure"])

    def test_deterministic_replay_stress_1000_events(self):
        recorded_journal: list[Event] = []
        for i in range(1000):
            event = Event(
                event_id=f"evt_{i:04d}",
                causation_id=f"evt_{i-1:04d}" if i > 0 else "root_intent",
                correlation_id="sess_stress_1000"
            )
            recorded_journal.append(event)

        replayed_stream: list[Event] = []
        target_transport = InMemoryTransport()
        target_transport.subscribe(Event, lambda e: replayed_stream.append(e))

        replay_engine = DeterministicReplayEngine(target_transport)
        count = replay_engine.replay_journal(recorded_journal)

        self.assertEqual(count, 1000)
        self.assertEqual(len(replayed_stream), 1000)

        result = DeterministicReplayEngine.verify_replayed_lineage(recorded_journal, replayed_stream)
        self.assertTrue(result["match"])

if __name__ == "__main__":
    unittest.main()
