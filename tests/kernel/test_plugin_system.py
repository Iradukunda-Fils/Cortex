"""
Plugin System & Capability Negotiation Test Suite
"""

import unittest

from typing_extensions import override

from cortex.tools.kernel.plugin.loader import (
    PluginRegistry,
    PluginState,
)
from cortex.tools.kernel.plugin.manifest import (
    AGENT_PLANNER_MANIFEST,
    ROBOT_ARM_MANIFEST,
    VERIFICATION_SERVICE_MANIFEST,
)


class TestPluginManifest(unittest.TestCase):
    def test_manifest_immutability(self):
        """Plugin manifests must be frozen (immutable after creation)."""
        m = ROBOT_ARM_MANIFEST
        with self.assertRaises(AttributeError):
            m.name = "tampered"  # pyright: ignore[reportAttributeAccessIssue]

    def test_manifest_event_contract(self):
        """Verify canonical manifest event declarations."""
        self.assertIn("CommandIssuedEvent", ROBOT_ARM_MANIFEST.consumes_events)
        self.assertIn("DriverTelemetryEvent", ROBOT_ARM_MANIFEST.produces_events)
        self.assertIn("IntentEvent", AGENT_PLANNER_MANIFEST.consumes_events)
        self.assertIn("PlanGeneratedEvent", AGENT_PLANNER_MANIFEST.produces_events)
        self.assertIn("CommitEventV1", VERIFICATION_SERVICE_MANIFEST.consumes_events)


class TestCapabilityNegotiation(unittest.TestCase):
    platform_caps: set[str] = set()

    @override
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
        _ = registry.register(ROBOT_ARM_MANIFEST)
        _ = registry.register(AGENT_PLANNER_MANIFEST)
        _ = registry.register(VERIFICATION_SERVICE_MANIFEST)

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
        _ = registry.register(AGENT_PLANNER_MANIFEST)
        p = registry.get_plugin("llm-task-planner")

        self.assertIsNotNone(p)
        assert p is not None
        self.assertEqual(p.manifest.name, "llm-task-planner")
        self.assertEqual(p.state, PluginState.ACTIVE)


if __name__ == "__main__":
    _ = unittest.main()
