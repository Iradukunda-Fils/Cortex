"""
Plugin Contract & Ecosystem Verification Test Suite (Issue #6)

Validates manifest validation (ManifestError), runtime plugin exception isolation,
instance context isolation, event routing enforcement, causal lineage preservation,
and duplicate registration idempotency.
"""

import unittest

from cortex import (
    BaseEvent,
    BasePlugin,
    CommandIssuedEvent,
    CortexClient,
    DriverTelemetryEvent,
    IntentEvent,
    ManifestError,
    PluginManifest,
    VerificationResultEvent,
    WorkflowState,
)
from cortex.compat import override
from cortex.tools.kernel.plugin.manifest import validate_manifest


class TestPluginManifestStructuralValidation(unittest.TestCase):
    """Test structural PluginManifest validation rules."""

    def test_valid_manifest_passes_validation(self) -> None:
        """Valid PluginManifest passes validate_manifest without raising."""
        manifest = PluginManifest(
            name="valid-plugin",
            version="1.0.0",
            description="Valid test manifest",
            consumes_events=["IntentEvent"],
            produces_events=["PlanGeneratedEvent"],
            required_capabilities=["workflow.plan.create"],
        )
        validate_manifest(manifest)

    def test_empty_name_raises_manifest_error(self) -> None:
        """PluginManifest with empty or whitespace name raises ManifestError."""
        with self.assertRaises(ManifestError) as ctx:
            manifest = PluginManifest(
                name="",
                version="1.0.0",
                description="Test",
            )
            validate_manifest(manifest)
        self.assertIn("name", str(ctx.exception))

    def test_empty_version_raises_manifest_error(self) -> None:
        """PluginManifest with empty version string raises ManifestError."""
        with self.assertRaises(ManifestError) as ctx:
            manifest = PluginManifest(
                name="test-plugin",
                version="  ",
                description="Test",
            )
            validate_manifest(manifest)
        self.assertIn("version", str(ctx.exception))

    def test_invalid_consumes_events_element_raises_manifest_error(self) -> None:
        """Non-string elements in consumes_events raise ManifestError."""
        with self.assertRaises(ManifestError) as ctx:
            manifest = PluginManifest(
                name="test-plugin",
                version="1.0.0",
                description="Test",
                consumes_events=["IntentEvent", ""],  # Empty string element
            )
            validate_manifest(manifest)
        self.assertIn("consumes_events", str(ctx.exception))

    def test_invalid_required_capabilities_element_raises_manifest_error(self) -> None:
        """Non-string elements in required_capabilities raise ManifestError."""
        with self.assertRaises(ManifestError) as ctx:
            manifest = PluginManifest(
                name="test-plugin",
                version="1.0.0",
                description="Test",
                required_capabilities=[""],
            )
            validate_manifest(manifest)
        self.assertIn("required_capabilities", str(ctx.exception))

    def test_invalid_object_type_raises_manifest_error(self) -> None:
        """Passing non-PluginManifest object to validate_manifest raises ManifestError."""
        with self.assertRaises(ManifestError):
            validate_manifest("not_a_manifest")  # type: ignore[arg-type]


class TestPluginRuntimeExceptionIsolation(unittest.TestCase):
    """Test host process protection from uncaught plugin exceptions."""

    def test_uncaught_plugin_exception_is_trapped_and_fails_workflow(self) -> None:
        """Plugin throwing ZeroDivisionError in on_event does not crash host and marks workflow FAILED."""
        manifest = PluginManifest(
            name="crashing-plugin",
            version="0.1.0",
            description="Plugin that crashes on event",
            consumes_events=["IntentEvent"],
            produces_events=[],
            required_capabilities=["workflow.plan.create"],
        )

        class CrashingPlugin(BasePlugin):
            def __init__(self) -> None:
                super().__init__(manifest)

            @override
            def on_event(self, event: BaseEvent) -> None:
                _ = 1 / 0  # Trigger ZeroDivisionError

        client = CortexClient()
        client.register_plugin(CrashingPlugin())

        wf = client.create_workflow(name="CrashTest", goal="Verify exception isolation")
        intent = IntentEvent(workflow_id=wf.workflow_id, goal="Trigger crash")
        executed_wf = client.run_workflow(wf, initial_intent=intent)

        # Host process survived, workflow transitioned to FAILED via canonical verification event
        self.assertEqual(executed_wf.state, WorkflowState.FAILED)

        log = client.event_store.get_log()
        verification_failures = [
            e for e in log if isinstance(e, VerificationResultEvent) and e.rule_id == "PLUGIN_EXECUTION_ERROR"
        ]
        self.assertEqual(len(verification_failures), 1)
        err_event = verification_failures[0]
        self.assertFalse(err_event.passed)
        self.assertEqual(err_event.details.get("plugin"), "crashing-plugin")
        self.assertEqual(err_event.details.get("error_type"), "ZeroDivisionError")


class TestPluginInstanceIsolation(unittest.TestCase):
    """Test state and context isolation between plugin instances."""

    def test_multiple_plugin_instances_have_independent_contexts(self) -> None:
        """Two instances of the same plugin class receive distinct PluginContext instances."""
        manifest1 = PluginManifest(
            name="instance-1",
            version="0.1.0",
            description="Instance 1",
            consumes_events=["IntentEvent"],
            required_capabilities=["workflow.plan.create"],
        )
        manifest2 = PluginManifest(
            name="instance-2",
            version="0.1.0",
            description="Instance 2",
            consumes_events=["IntentEvent"],
            required_capabilities=["fs:read"],
        )

        class IsolationTestPlugin(BasePlugin):
            @override
            def on_event(self, event: BaseEvent) -> None:
                pass

        p1 = IsolationTestPlugin(manifest1)
        p2 = IsolationTestPlugin(manifest2)

        client = CortexClient()
        client.register_plugin(p1)
        client.register_plugin(p2)

        self.assertIsNotNone(p1.context)
        self.assertIsNotNone(p2.context)
        self.assertIsNot(p1.context, p2.context)

        assert p1.context is not None
        assert p2.context is not None

        self.assertTrue(p1.context.has_capability("workflow.plan.create"))
        self.assertFalse(p1.context.has_capability("fs:read"))

        self.assertTrue(p2.context.has_capability("fs:read"))
        self.assertFalse(p2.context.has_capability("workflow.plan.create"))


class TestPluginEventRoutingAndLineage(unittest.TestCase):
    """Test event routing enforcement and causal lineage propagation."""

    def test_plugin_only_receives_declared_consumed_events(self) -> None:
        """Plugin declaring consumes_events=['IntentEvent'] does not receive CommandIssuedEvent."""
        received_events: list[BaseEvent] = []

        manifest = PluginManifest(
            name="intent-only-plugin",
            version="0.1.0",
            description="Consumes intent events only",
            consumes_events=["IntentEvent"],
            required_capabilities=["workflow.plan.create"],
        )

        class IntentOnlyPlugin(BasePlugin):
            def __init__(self) -> None:
                super().__init__(manifest)

            @override
            def on_event(self, event: BaseEvent) -> None:
                received_events.append(event)

        client = CortexClient()
        client.register_plugin(IntentOnlyPlugin())

        wf = client.create_workflow(name="RoutingTest", goal="Test event filtering")

        # Publish CommandIssuedEvent which is NOT in consumes_events
        cmd = CommandIssuedEvent(workflow_id=wf.workflow_id, action="test_action")
        client.transport.publish(cmd)

        self.assertEqual(len(received_events), 0)

        # Publish IntentEvent which IS in consumes_events
        intent = IntentEvent(workflow_id=wf.workflow_id, goal="test_goal")
        client.transport.publish(intent)

        self.assertEqual(len(received_events), 1)
        self.assertIsInstance(received_events[0], IntentEvent)

    def test_causal_lineage_preservation_across_plugins(self) -> None:
        """Events emitted by plugins preserve parent causation_id."""
        manifest = PluginManifest(
            name="lineage-plugin",
            version="0.1.0",
            description="Emits downstream telemetry",
            consumes_events=["IntentEvent"],
            produces_events=["DriverTelemetryEvent"],
            required_capabilities=["workflow.plan.create"],
        )

        class LineagePlugin(BasePlugin):
            def __init__(self) -> None:
                super().__init__(manifest)

            @override
            def on_event(self, event: BaseEvent) -> None:
                match event:
                    case IntentEvent() if self.context:
                        telemetry = DriverTelemetryEvent(
                            workflow_id=event.workflow_id,
                            causation_id=event.event_id,
                            driver_id="lineage_driver",
                            status="ok",
                            payload={"ok": True},
                        )
                        self.context.publish(telemetry)
                    case _:
                        pass

        client = CortexClient()
        client.register_plugin(LineagePlugin())

        wf = client.create_workflow(name="LineageTest", goal="Verify causation link")
        intent = IntentEvent(workflow_id=wf.workflow_id, goal="Test lineage")
        _ = client.run_workflow(wf, initial_intent=intent)

        log = client.event_store.get_log()
        telemetry_events = [e for e in log if isinstance(e, DriverTelemetryEvent)]
        self.assertEqual(len(telemetry_events), 1)
        self.assertEqual(telemetry_events[0].causation_id, intent.event_id)


class TestDuplicateRegistrationHandling(unittest.TestCase):
    """Audit duplicate plugin registration behavior."""

    def test_registering_same_plugin_instance_twice_is_idempotent(self) -> None:
        """Registering the exact same plugin instance twice returns existing registration without duplicating subscriptions."""
        manifest = PluginManifest(
            name="idempotent-plugin",
            version="0.1.0",
            description="Idempotent test plugin",
            consumes_events=["IntentEvent"],
            required_capabilities=["workflow.plan.create"],
        )

        counter = 0

        class IdempotentPlugin(BasePlugin):
            def __init__(self) -> None:
                super().__init__(manifest)

            @override
            def on_event(self, event: BaseEvent) -> None:
                nonlocal counter
                counter += 1

        plugin = IdempotentPlugin()
        client = CortexClient()

        reg1 = client.register_plugin(plugin)
        reg2 = client.register_plugin(plugin)

        self.assertIs(reg1, reg2)
        self.assertEqual(len(client.registered_plugins), 1)

        wf = client.create_workflow(name="IdempotencyTest", goal="Verify single execution")
        intent = IntentEvent(workflow_id=wf.workflow_id, goal="Test event")
        _ = client.run_workflow(wf, initial_intent=intent)

        # Counter should be 1 (not 2 from duplicate handlers)
        self.assertEqual(counter, 1)


if __name__ == "__main__":
    _ = unittest.main()
