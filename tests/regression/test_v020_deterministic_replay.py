"""
v0.2.0 Regression: Deterministic Replay via Public API

Validates EventStore persistence and deterministic replay through
CortexClient.save_trace → CortexClient.replay_workflow roundtrip.
"""

import json
import os
import shutil
import tempfile
import unittest
from typing import cast

from cortex import (
    BaseEvent,
    BasePlugin,
    CortexClient,
    IntentEvent,
    PlanGeneratedEvent,
    PluginManifest,
)
from cortex.compat import override


class ReplayTestPlugin(BasePlugin):
    """Plugin that produces events for replay validation."""

    @override
    def on_event(self, event: BaseEvent) -> None:
        if isinstance(event, IntentEvent) and self.context:
            self.context.publish(PlanGeneratedEvent(
                workflow_id=event.workflow_id,
                intent_id=event.intent_id,
                causation_id=event.event_id,
                steps=[{"step": 1, "action": "replay_test"}],
            ))

    def __init__(self) -> None:
        manifest = PluginManifest(
            name="replay-test-plugin",
            version="0.1.0",
            description="Plugin for replay regression testing",
            consumes_events=["IntentEvent"],
            produces_events=["PlanGeneratedEvent"],
            required_capabilities=["workflow.plan.create"],
        )
        super().__init__(manifest)


class TestDeterministicReplay(unittest.TestCase):
    """Validate trace save → load → replay determinism via CortexClient."""

    test_dir: str = ""

    @override
    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp(prefix="cortex_replay_regression_")

    @override
    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_and_replay_is_deterministic(self) -> None:
        """save_trace → replay_workflow roundtrip asserts determinism."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(ReplayTestPlugin())
        workflow = client.create_workflow(name="replay_wf", goal="Test replay")
        executed = client.run_workflow(workflow)

        trace_path = os.path.join(self.test_dir, "trace.json")
        _ = client.save_trace(executed.workflow_id, trace_path)

        replay_result = client.replay_workflow(trace_path)
        self.assertTrue(
            cast(bool, replay_result["deterministic"]),
            f"Replay was not deterministic: {replay_result.get('reason', '')}",
        )

    def test_trace_file_structure(self) -> None:
        """Saved trace JSON must contain expected v0.2.0 keys."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(ReplayTestPlugin())
        workflow = client.create_workflow(name="struct_wf", goal="Test structure")
        executed = client.run_workflow(workflow)

        trace_path = os.path.join(self.test_dir, "struct_trace.json")
        _ = client.save_trace(executed.workflow_id, trace_path, name="struct_wf", goal="Test structure")

        with open(trace_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        required_keys = {"name", "goal", "workflow_id", "event_count", "events"}
        actual_keys = set(data.keys())
        missing = required_keys - actual_keys
        self.assertEqual(
            missing, set(),
            f"Trace file missing required keys: {missing}",
        )

    def test_trace_event_count_matches_memory(self) -> None:
        """Event count in trace file must match in-memory event store."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(ReplayTestPlugin())
        workflow = client.create_workflow(name="count_wf", goal="Test count")
        executed = client.run_workflow(workflow)

        in_memory_count = len([
            e for e in client.event_store.get_log()
            if isinstance(e, BaseEvent)
        ])

        trace_path = os.path.join(self.test_dir, "count_trace.json")
        _ = client.save_trace(executed.workflow_id, trace_path)

        with open(trace_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["event_count"], in_memory_count)
        self.assertEqual(len(data["events"]), in_memory_count)

    def test_trace_events_have_type_marker(self) -> None:
        """Each serialized event in the trace must have _event_type key."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(ReplayTestPlugin())
        workflow = client.create_workflow(name="marker_wf", goal="Test markers")
        _ = client.run_workflow(workflow)

        trace_path = os.path.join(self.test_dir, "marker_trace.json")
        _ = client.save_trace(workflow.workflow_id, trace_path)

        with open(trace_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for i, event_dict in enumerate(data["events"]):
            with self.subTest(event_index=i):
                self.assertIn(
                    "_event_type", event_dict,
                    f"Event at index {i} missing _event_type marker",
                )

    def test_replay_event_count_matches_original(self) -> None:
        """Replay must process the same number of events as the original execution."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(ReplayTestPlugin())
        workflow = client.create_workflow(name="replay_count_wf", goal="Test replay count")
        executed = client.run_workflow(workflow)

        in_memory_count = len([
            e for e in client.event_store.get_log()
            if isinstance(e, BaseEvent)
        ])

        trace_path = os.path.join(self.test_dir, "replay_count_trace.json")
        _ = client.save_trace(executed.workflow_id, trace_path)

        replay_result = client.replay_workflow(trace_path)
        self.assertEqual(
            cast(int, replay_result["replayed_count"]),
            in_memory_count,
        )


if __name__ == "__main__":
    _ = unittest.main()
