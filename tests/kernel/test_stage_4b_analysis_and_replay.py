"""
Stage 4B Execution Graph Analysis & Deterministic Replay Test Suite
"""

import unittest
from tools.kernel.transport import InMemoryTransport
from tools.kernel.context import RuntimeContext
from tools.kernel.schema.message import Intent, Plan, Command, DriverTelemetryEvent, VerificationResultEvent, Event
from tools.kernel.graph.execution_graph import ExecutionGraph
from tools.kernel.graph.analyzer import ExecutionGraphAnalyzer
from tools.kernel.services.replay import DeterministicReplayEngine
from tools.kernel.services.graph_builder import ExecutionGraphBuilderService

class TestStage4BAnalysisAndReplay(unittest.TestCase):
    def setUp(self):
        self.transport = InMemoryTransport()
        self.context = RuntimeContext("stage_4b_actor", "sess_4b", self.transport)
        self.graph_builder = ExecutionGraphBuilderService()

    def test_root_cause_analysis_and_graph_diff(self):
        # 1. Build a synthetic execution graph with a failed node
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

        # 2. Assert failed node identification
        failed_nodes = analyzer.find_failed_nodes()
        self.assertEqual(len(failed_nodes), 1)
        self.assertEqual(failed_nodes[0].node_id, verif_fail.event_id)

        # 3. Trace root cause path back to Intent
        lineage_path = analyzer.find_root_cause(verif_fail.event_id)
        node_types = [n.node_type for n in lineage_path]
        self.assertEqual(node_types, ["Verification", "Telemetry", "Command", "Plan", "Intent"])
        self.assertEqual(lineage_path[-1].node_id, intent.intent_id)

        # 4. Compare with identical golden graph
        diff = ExecutionGraphAnalyzer.diff_graphs(graph, graph)
        self.assertTrue(diff["identical_structure"])
        self.assertEqual(diff["node_count_diff"], 0)

    def test_deterministic_replay_stress_1000_events(self):
        # Generate 1,000 synthetic events
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

        # Confirm 100% deterministic lineage match
        result = DeterministicReplayEngine.verify_replayed_lineage(recorded_journal, replayed_stream)
        self.assertTrue(result["match"])
        print(f"\n[✓] 1,000-Event Deterministic Replay Result: {result['reason']}")

if __name__ == "__main__":
    unittest.main()
