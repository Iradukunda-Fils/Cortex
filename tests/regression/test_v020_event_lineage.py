"""
v0.2.0 Regression: Event Causal Lineage Validation

Validates that every event produced by a CortexClient workflow execution
carries correct causal lineage metadata (event_id, causation_id,
correlation_id, root_id, timestamp_ns).
"""

import shutil
import tempfile
import unittest
import uuid

from cortex import (
    BaseEvent,
    BasePlugin,
    CortexClient,
    IntentEvent,
    PlanGeneratedEvent,
    PluginManifest,
)
from cortex.compat import override


class LineageTestPlugin(BasePlugin):
    """Plugin that emits a PlanGeneratedEvent with explicit causation linkage."""

    @override
    def on_event(self, event: BaseEvent) -> None:
        if isinstance(event, IntentEvent) and self.context:
            plan = PlanGeneratedEvent(
                workflow_id=event.workflow_id,
                intent_id=event.intent_id,
                causation_id=event.event_id,
                correlation_id=event.correlation_id,
                root_id=event.root_id or event.event_id,
                steps=[{"step": 1, "action": "lineage_test"}],
            )
            self.context.publish(plan)

    def __init__(self) -> None:
        manifest = PluginManifest(
            name="lineage-test-plugin",
            version="0.1.0",
            description="Plugin for lineage regression testing",
            consumes_events=["IntentEvent"],
            produces_events=["PlanGeneratedEvent"],
            required_capabilities=["workflow.plan.create"],
        )
        super().__init__(manifest)


class TestEventLineage(unittest.TestCase):
    """Black-box lineage validation via CortexClient public API."""

    test_dir: str = ""

    @override
    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp(prefix="cortex_lineage_")

    @override
    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_all_events_have_non_empty_event_id(self) -> None:
        """Every recorded event must have a non-empty UUID-format event_id."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(LineageTestPlugin())
        workflow = client.create_workflow(name="lineage_wf", goal="Test lineage")
        _ = client.run_workflow(workflow)

        events = client.event_store.get_log()
        self.assertGreater(len(events), 0, "No events recorded")

        for event in events:
            if isinstance(event, BaseEvent):
                with self.subTest(event_type=type(event).__name__):
                    self.assertTrue(
                        len(event.event_id) > 0,
                        f"Empty event_id on {type(event).__name__}",
                    )
                    # Validate UUID format
                    try:
                        uuid.UUID(event.event_id)
                    except ValueError:
                        self.fail(f"event_id '{event.event_id}' is not valid UUID")

    def test_non_root_events_have_causation_chain(self) -> None:
        """Non-root events produced by plugins must have a causation_id linking to parent."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(LineageTestPlugin())
        workflow = client.create_workflow(name="causation_wf", goal="Test causation")
        _ = client.run_workflow(workflow)

        events = [e for e in client.event_store.get_log() if isinstance(e, BaseEvent)]
        plan_events = [e for e in events if isinstance(e, PlanGeneratedEvent)]

        self.assertGreater(len(plan_events), 0, "No PlanGeneratedEvents produced")
        for plan in plan_events:
            self.assertIsNotNone(
                plan.causation_id,
                "PlanGeneratedEvent must have causation_id linking to IntentEvent",
            )

    def test_timestamp_ns_is_positive(self) -> None:
        """All events must have a positive nanosecond timestamp."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(LineageTestPlugin())
        workflow = client.create_workflow(name="ts_wf", goal="Test timestamps")
        _ = client.run_workflow(workflow)

        events = [e for e in client.event_store.get_log() if isinstance(e, BaseEvent)]
        for event in events:
            with self.subTest(event_type=type(event).__name__):
                self.assertGreater(
                    event.timestamp_ns, 0,
                    f"timestamp_ns must be positive, got {event.timestamp_ns}",
                )

    def test_workflow_id_propagates_through_events(self) -> None:
        """Events produced during workflow execution must carry the workflow_id."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(LineageTestPlugin())
        workflow = client.create_workflow(name="wfid_wf", goal="Test wf_id propagation")
        executed = client.run_workflow(workflow)

        events = [e for e in client.event_store.get_log() if isinstance(e, BaseEvent)]
        intent_events = [e for e in events if isinstance(e, IntentEvent)]

        self.assertGreater(len(intent_events), 0)
        for intent in intent_events:
            self.assertEqual(
                intent.workflow_id,
                executed.workflow_id,
                "IntentEvent.workflow_id must match executed workflow",
            )


if __name__ == "__main__":
    _ = unittest.main()
