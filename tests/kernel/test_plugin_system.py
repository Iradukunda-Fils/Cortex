"""
Plugin System & Capability Negotiation Test Suite
"""

import unittest
from tools.kernel.plugin.manifest import (
    PluginManifest,
    ROBOT_ARM_MANIFEST,
    AGENT_PLANNER_MANIFEST,
    VERIFICATION_SERVICE_MANIFEST,
)
from tools.kernel.plugin.loader import (
    PluginRegistry,
    PluginState,
    CapabilityNegotiator,
)


class TestPluginManifest(unittest.TestCase):
    def test_manifest_immutability(self):
        """Plugin manifests must be frozen (immutable after creation)."""
        m = ROBOT_ARM_MANIFEST
        with self.assertRaises(AttributeError):
            m.name = "tampered"

    def test_manifest_event_contract(self):
        """Verify canonical manifest event declarations."""
        self.assertIn("CommandIssuedEvent", ROBOT_ARM_MANIFEST.consumes_events)
        self.assertIn("DriverTelemetryEvent", ROBOT_ARM_MANIFEST.produces_events)
        self.assertIn("IntentEvent", AGENT_PLANNER_MANIFEST.consumes_events)
        self.assertIn("PlanGeneratedEvent", AGENT_PLANNER_MANIFEST.produces_events)
        self.assertIn("CommitEventV1", VERIFICATION_SERVICE_MANIFEST.consumes_events)


class TestCapabilityNegotiation(unittest.TestCase):
    def setUp(self):
        self.platform_caps = {
            "hardware.actuators.execute",
            "hardware.telemetry.read",
            "workflow.plan.create",
            "verification.oracle.execute",
            "verification.invariant.check",
        }

    def test_full_grant_plugin(self):
        """Plugin requesting only available capabilities is ACTIVE."""
        registry = PluginRegistry(self.platform_caps)
        reg = registry.register(ROBOT_ARM_MANIFEST)

        self.assertEqual(reg.state, PluginState.ACTIVE)
        self.assertEqual(len(reg.denied_capabilities), 0)
        self.assertEqual(reg.granted_capabilities, {"hardware.actuators.execute", "hardware.telemetry.read"})

    def test_partial_deny_plugin(self):
        """Plugin requesting unavailable capabilities is REJECTED."""
        restricted_caps = {"workflow.plan.create"}
        registry = PluginRegistry(restricted_caps)
        reg = registry.register(ROBOT_ARM_MANIFEST)

        self.assertEqual(reg.state, PluginState.REJECTED)
        self.assertIn("hardware.actuators.execute", reg.denied_capabilities)

    def test_multi_plugin_registry(self):
        """Multiple plugins can be registered and queried by state."""
        registry = PluginRegistry(self.platform_caps)
        registry.register(ROBOT_ARM_MANIFEST)
        registry.register(AGENT_PLANNER_MANIFEST)
        registry.register(VERIFICATION_SERVICE_MANIFEST)

        active = registry.get_active_plugins()
        self.assertEqual(len(active), 3)

    def test_sandbox_isolation_no_raw_kernel_access(self):
        """A rejected plugin receives zero granted capabilities."""
        registry = PluginRegistry(set())  # Empty platform — nothing available
        reg = registry.register(ROBOT_ARM_MANIFEST)

        self.assertEqual(reg.state, PluginState.REJECTED)
        self.assertEqual(len(reg.granted_capabilities), 0)
        self.assertEqual(len(reg.denied_capabilities), 2)

    def test_plugin_lookup(self):
        """Plugins can be retrieved by name."""
        registry = PluginRegistry(self.platform_caps)
        registry.register(AGENT_PLANNER_MANIFEST)
        p = registry.get_plugin("llm-task-planner")

        self.assertIsNotNone(p)
        self.assertEqual(p.manifest.name, "llm-task-planner")
        self.assertEqual(p.state, PluginState.ACTIVE)


if __name__ == "__main__":
    unittest.main()
