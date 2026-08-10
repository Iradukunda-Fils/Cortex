"""
v0.2.0 Regression: Capability Enforcement via Public API

Black-box capability negotiation tests using CortexClient.
Validates ACTIVE/REJECTED plugin states and VerificationResultEvent emission.
"""

import unittest

from cortex import (
    BaseEvent,
    BasePlugin,
    CortexClient,
    IntentEvent,
    PlanGeneratedEvent,
    PluginManifest,
    VerificationResultEvent,
    WorkflowState,
)
from cortex.compat import override


class FullGrantPlugin(BasePlugin):
    """Plugin that requests only standard capabilities."""

    @override
    def on_event(self, event: BaseEvent) -> None:
        if isinstance(event, IntentEvent) and self.context:
            self.context.publish(PlanGeneratedEvent(
                workflow_id=event.workflow_id,
                intent_id=event.intent_id,
                causation_id=event.event_id,
                steps=[{"step": 1, "action": "granted_action"}],
            ))

    def __init__(self) -> None:
        manifest = PluginManifest(
            name="full-grant-plugin",
            version="0.1.0",
            description="Requests only available capabilities",
            consumes_events=["IntentEvent"],
            produces_events=["PlanGeneratedEvent"],
            required_capabilities=["workflow.plan.create"],
        )
        super().__init__(manifest)


class ExcessCapabilityPlugin(BasePlugin):
    """Plugin that requests capabilities NOT available on the platform."""

    @override
    def on_event(self, event: BaseEvent) -> None:
        pass  # Should never be called — plugin is REJECTED

    def __init__(self) -> None:
        manifest = PluginManifest(
            name="excess-capability-plugin",
            version="0.1.0",
            description="Requests unavailable capabilities",
            consumes_events=["IntentEvent"],
            produces_events=[],
            required_capabilities=["hardware.actuators.execute", "nuclear.launch.authorize"],
        )
        super().__init__(manifest)


class TestCapabilityEnforcement(unittest.TestCase):
    """Black-box capability tests via CortexClient public API."""

    def test_full_grant_plugin_is_active(self) -> None:
        """Plugin requesting available capabilities is registered as ACTIVE."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        reg = client.register_plugin(FullGrantPlugin())
        self.assertEqual(reg.state.value, "ACTIVE")

    def test_full_grant_workflow_completes(self) -> None:
        """Workflow with fully-granted plugin completes successfully."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(FullGrantPlugin())
        workflow = client.create_workflow(name="grant_wf", goal="Test full grant")
        executed = client.run_workflow(workflow)
        self.assertEqual(executed.state, WorkflowState.COMPLETED)

    def test_excess_capability_plugin_is_rejected(self) -> None:
        """Plugin requesting unavailable capabilities is REJECTED."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        reg = client.register_plugin(ExcessCapabilityPlugin())
        self.assertEqual(reg.state.value, "REJECTED")

    def test_rejected_plugin_workflow_fails(self) -> None:
        """Workflow with rejected plugin transitions to FAILED."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(ExcessCapabilityPlugin())
        workflow = client.create_workflow(name="reject_wf", goal="Test rejection")
        executed = client.run_workflow(workflow)
        self.assertEqual(executed.state, WorkflowState.FAILED)

    def test_capability_violation_event_emitted(self) -> None:
        """Rejected plugins cause a VerificationResultEvent with CAPABILITY_VIOLATION."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(ExcessCapabilityPlugin())
        workflow = client.create_workflow(name="violation_wf", goal="Test violation event")
        _ = client.run_workflow(workflow)

        events = [
            e for e in client.event_store.get_log()
            if isinstance(e, VerificationResultEvent)
        ]
        self.assertGreater(len(events), 0, "No VerificationResultEvent emitted")
        violation = events[0]
        self.assertFalse(violation.passed)
        self.assertEqual(violation.rule_id, "CAPABILITY_VIOLATION")

    def test_empty_platform_rejects_all_plugins(self) -> None:
        """Zero platform capabilities rejects any plugin with required capabilities."""
        client = CortexClient(platform_capabilities=set())
        reg = client.register_plugin(FullGrantPlugin())
        self.assertEqual(reg.state.value, "REJECTED")
        self.assertGreater(len(reg.denied_capabilities), 0)

    def test_rejected_plugin_has_zero_granted_capabilities(self) -> None:
        """Rejected plugins receive an empty granted capabilities set."""
        client = CortexClient(platform_capabilities=set())
        reg = client.register_plugin(FullGrantPlugin())
        self.assertEqual(len(reg.granted_capabilities), 0)


if __name__ == "__main__":
    _ = unittest.main()
