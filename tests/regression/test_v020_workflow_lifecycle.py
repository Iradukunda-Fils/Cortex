"""
v0.2.0 Regression: Workflow Lifecycle State Machine

Validates workflow state transitions via CortexClient public API.
"""

import unittest

from cortex import (
    BaseEvent,
    BasePlugin,
    CortexClient,
    IntentEvent,
    PlanGeneratedEvent,
    PluginManifest,
    Workflow,
    WorkflowPolicy,
    WorkflowState,
)
from cortex.compat import override


class LifecyclePlugin(BasePlugin):
    """Simple plugin for lifecycle testing."""

    @override
    def on_event(self, event: BaseEvent) -> None:
        if isinstance(event, IntentEvent) and self.context:
            self.context.publish(PlanGeneratedEvent(
                workflow_id=event.workflow_id,
                intent_id=event.intent_id,
                causation_id=event.event_id,
                steps=[{"step": 1, "action": "lifecycle_step"}],
            ))

    def __init__(self) -> None:
        manifest = PluginManifest(
            name="lifecycle-plugin",
            version="0.1.0",
            description="Plugin for lifecycle testing",
            consumes_events=["IntentEvent"],
            produces_events=["PlanGeneratedEvent"],
            required_capabilities=["workflow.plan.create"],
        )
        super().__init__(manifest)


class TestWorkflowLifecycle(unittest.TestCase):
    """Assert workflow state machine transitions via CortexClient."""

    def test_create_workflow_is_pending(self) -> None:
        """Newly created workflow must be in PENDING state."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        workflow = client.create_workflow(name="pending_wf", goal="Test pending")
        self.assertEqual(workflow.state, WorkflowState.PENDING)

    def test_successful_workflow_is_completed(self) -> None:
        """Workflow with active plugin transitions PENDING → COMPLETED."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(LifecyclePlugin())
        workflow = client.create_workflow(name="success_wf", goal="Test success")
        executed = client.run_workflow(workflow)
        self.assertEqual(executed.state, WorkflowState.COMPLETED)

    def test_rejected_plugin_workflow_is_failed(self) -> None:
        """Workflow with rejected plugin transitions PENDING → FAILED."""
        client = CortexClient(platform_capabilities=set())  # Empty platform
        _ = client.register_plugin(LifecyclePlugin())
        workflow = client.create_workflow(name="fail_wf", goal="Test failure")
        executed = client.run_workflow(workflow)
        self.assertEqual(executed.state, WorkflowState.FAILED)

    def test_workflow_has_uuid_id(self) -> None:
        """Workflow must have a non-empty workflow_id."""
        client = CortexClient()
        workflow = client.create_workflow(name="id_wf", goal="Test ID")
        self.assertTrue(len(workflow.workflow_id) > 0)

    def test_workflow_preserves_name_and_goal(self) -> None:
        """Workflow must preserve name and goal exactly as provided."""
        client = CortexClient()
        workflow = client.create_workflow(name="exact_name", goal="exact_goal")
        self.assertEqual(workflow.name, "exact_name")
        self.assertEqual(workflow.goal, "exact_goal")

    def test_workflow_default_policy(self) -> None:
        """Workflow with no explicit policy uses default values."""
        client = CortexClient()
        workflow = client.create_workflow(name="policy_wf", goal="Test policy")
        self.assertEqual(workflow.policy.timeout_seconds, 300.0)
        self.assertEqual(workflow.policy.max_retries, 3)
        self.assertTrue(workflow.policy.abort_on_verification_failure)

    def test_workflow_custom_policy(self) -> None:
        """Workflow accepts custom policy parameters."""
        client = CortexClient()
        policy = WorkflowPolicy(timeout_seconds=60.0, max_retries=1, abort_on_verification_failure=False)
        workflow = client.create_workflow(name="custom_wf", goal="Custom policy", policy=policy)
        self.assertEqual(workflow.policy.timeout_seconds, 60.0)
        self.assertEqual(workflow.policy.max_retries, 1)
        self.assertFalse(workflow.policy.abort_on_verification_failure)

    def test_workflow_produces_events_in_event_store(self) -> None:
        """Running a workflow must produce at least one event in the event store."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(LifecyclePlugin())
        workflow = client.create_workflow(name="events_wf", goal="Test events")
        _ = client.run_workflow(workflow)
        events = client.event_store.get_log()
        self.assertGreater(len(events), 0)

    def test_workflow_dataclass_fields(self) -> None:
        """Workflow dataclass must expose v0.2.0 fields."""
        wf = Workflow(name="field_test", goal="Test fields")
        self.assertIsNotNone(wf.workflow_id)
        self.assertEqual(wf.state, WorkflowState.PENDING)
        self.assertIsNotNone(wf.policy)
        self.assertIsNone(wf.root_intent_id)
        self.assertIsNone(wf.execution_graph_id)
        self.assertGreater(wf.created_at_ns, 0)


if __name__ == "__main__":
    _ = unittest.main()
