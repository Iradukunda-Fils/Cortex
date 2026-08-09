"""
Public CortexClient API Unit & Integration Test Suite
"""

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
    WorkflowState,
)
from cortex.compat import override


class SamplePublicPlugin(BasePlugin):
    @override
    def on_event(self, event: BaseEvent) -> None:
        if isinstance(event, IntentEvent) and self.context:
            plan = PlanGeneratedEvent(
                workflow_id=event.workflow_id,
                intent_id=event.intent_id,
                causation_id=event.event_id,
                steps=[{"step": 1, "action": "sample_step"}],
            )
            self.context.publish(plan)

    def __init__(self) -> None:
        manifest = PluginManifest(
            name="sample-public-plugin",
            version="0.1.0",
            description="Sample plugin using public API",
            consumes_events=["IntentEvent"],
            produces_events=["PlanGeneratedEvent"],
            required_capabilities=["workflow.plan.create"],
        )
        super().__init__(manifest)


class TestPublicAPI(unittest.TestCase):
    test_dir: str = ""

    @override
    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp(prefix="cortex_pub_api_")

    @override
    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_client_workflow_lifecycle(self) -> None:
        """Test full workflow creation, plugin registration, and execution via CortexClient."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        plugin = SamplePublicPlugin()
        reg = client.register_plugin(plugin)

        self.assertEqual(reg.state.value, "ACTIVE")

        workflow = client.create_workflow(name="public_wf", goal="Test Public API")
        executed = client.run_workflow(workflow)

        self.assertEqual(executed.state, WorkflowState.COMPLETED)
        self.assertGreaterEqual(len(client.event_store.get_log()), 2)

    def test_save_inspect_replay_trace(self) -> None:
        """Test trace saving, graph inspection, and deterministic replay via CortexClient."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(SamplePublicPlugin())
        workflow = client.create_workflow(name="trace_wf", goal="Test Trace Ops")
        executed = client.run_workflow(workflow)

        trace_path = os.path.join(self.test_dir, "trace.json")
        _ = client.save_trace(executed.workflow_id, trace_path)
        self.assertTrue(os.path.exists(trace_path))

        inspection = client.inspect_workflow(trace_path)
        node_count = cast(int, inspection["node_count"])
        self.assertGreaterEqual(node_count, 1)

        replay_res = client.replay_workflow(trace_path)
        self.assertTrue(cast(bool, replay_res["deterministic"]))


if __name__ == "__main__":
    _ = unittest.main()
