"""
v0.2.0 Regression: Public API Surface Contract

Freezes the exact set of symbols exported from `cortex.__init__.__all__`
and validates that each symbol is importable, of the expected type,
has complete documentation, and that no internal kernel symbols leak
through the public boundary.
"""

import enum
import importlib
import unittest
from abc import ABC
from dataclasses import fields, is_dataclass
from typing import Any

import cortex

# Frozen v0.2.0 public API surface — 21 symbols
V020_PUBLIC_SYMBOLS = frozenset({
    "BaseEvent",
    "BasePlugin",
    "Capability",
    "CapabilityViolationError",
    "CommandIssuedEvent",
    "CortexClient",
    "CortexError",
    "DriverTelemetryEvent",
    "EventStore",
    "IntentEvent",
    "ManifestError",
    "PlanGeneratedEvent",
    "PluginContext",
    "PluginManifest",
    "TelemetryEvent",
    "VerificationResultEvent",
    "Workflow",
    "WorkflowExecutionError",
    "WorkflowPolicy",
    "WorkflowState",
    "override",
})

# Internal subpackages that must NOT re-export symbols via wildcard imports
INTERNAL_PACKAGES = [
    "cortex.tools",
    "cortex.tools.cli",
    "cortex.tools.kernel",
    "cortex.tools.kernel.actors",
    "cortex.tools.kernel.drivers",
    "cortex.tools.kernel.graph",
    "cortex.tools.kernel.plugin",
    "cortex.tools.kernel.schema",
    "cortex.tools.kernel.services",
    "cortex.tools.verification",
    "cortex.tools.verification.adapters",
    "cortex.tools.verification.generator",
    "cortex.tools.verification.invariants",
    "cortex.tools.verification.metrics",
    "cortex.tools.verification.schema",
]


class TestPublicAPISurface(unittest.TestCase):
    """Freeze-test: public API boundary must not shrink or shift."""

    def test_all_exports_match_v020_baseline(self) -> None:
        """cortex.__all__ must contain exactly the v0.2.0 symbol set."""
        actual = frozenset(cortex.__all__)
        missing = V020_PUBLIC_SYMBOLS - actual
        unexpected = actual - V020_PUBLIC_SYMBOLS
        self.assertEqual(
            missing,
            frozenset(),
            f"Symbols removed from public API (breaking change): {missing}",
        )
        self.assertEqual(
            unexpected,
            frozenset(),
            f"Symbols added to public API without regression update: {unexpected}",
        )

    def test_all_symbols_importable(self) -> None:
        """Every symbol in __all__ must be importable from the cortex package."""
        for symbol_name in V020_PUBLIC_SYMBOLS:
            with self.subTest(symbol=symbol_name):
                self.assertTrue(
                    hasattr(cortex, symbol_name),
                    f"Symbol '{symbol_name}' declared in __all__ but not importable",
                )

    def test_event_types_are_frozen_dataclasses(self) -> None:
        """All event types must be frozen (immutable) dataclasses."""
        event_names = [
            "BaseEvent",
            "IntentEvent",
            "PlanGeneratedEvent",
            "CommandIssuedEvent",
            "DriverTelemetryEvent",
            "VerificationResultEvent",
        ]
        for name in event_names:
            with self.subTest(event_type=name):
                cls = getattr(cortex, name)
                self.assertTrue(is_dataclass(cls), f"{name} is not a dataclass")
                # Frozen dataclasses have __dataclass_params__.frozen == True
                params: Any = getattr(cls, "__dataclass_params__", None)
                self.assertIsNotNone(params, f"{name} missing __dataclass_params__")
                assert params is not None
                self.assertTrue(params.frozen, f"{name} is not frozen")

    def test_base_event_has_lineage_fields(self) -> None:
        """BaseEvent must carry the v0.2.0 causal lineage field set."""
        required_fields = {
            "event_id", "workflow_id", "causation_id",
            "correlation_id", "root_id", "timestamp_ns", "metadata",
        }
        actual_fields = {f.name for f in fields(cortex.BaseEvent)}
        missing = required_fields - actual_fields
        self.assertEqual(
            missing,
            set(),
            f"BaseEvent missing required lineage fields: {missing}",
        )

    def test_workflow_state_enum_values(self) -> None:
        """WorkflowState must have exactly the v0.2.0 state set."""
        expected = {"PENDING", "RUNNING", "COMPLETED", "FAILED", "ABORTED"}
        actual = {s.value for s in cortex.WorkflowState}
        self.assertEqual(actual, expected)

    def test_workflow_state_is_str_enum(self) -> None:
        """WorkflowState must be a str enum for JSON serialization."""
        self.assertTrue(issubclass(cortex.WorkflowState, str))
        self.assertTrue(issubclass(cortex.WorkflowState, enum.Enum))

    def test_base_plugin_is_abstract(self) -> None:
        """BasePlugin must be an abstract base class."""
        self.assertTrue(issubclass(cortex.BasePlugin, ABC))

    def test_capability_is_frozen_dataclass(self) -> None:
        """Capability must be a frozen dataclass with a 'name' field."""
        self.assertTrue(is_dataclass(cortex.Capability))
        params: Any = getattr(cortex.Capability, "__dataclass_params__", None)
        self.assertIsNotNone(params)
        assert params is not None
        self.assertTrue(params.frozen)
        field_names = {f.name for f in fields(cortex.Capability)}
        self.assertIn("name", field_names)

    def test_exception_hierarchy(self) -> None:
        """All Cortex exceptions must inherit from CortexError → Exception."""
        self.assertTrue(issubclass(cortex.CortexError, Exception))
        self.assertTrue(issubclass(cortex.WorkflowExecutionError, cortex.CortexError))
        self.assertTrue(issubclass(cortex.CapabilityViolationError, cortex.CortexError))
        self.assertTrue(issubclass(cortex.ManifestError, cortex.CortexError))

    def test_exception_exit_codes(self) -> None:
        """Exception subclasses must have stable exit codes."""
        self.assertEqual(cortex.CortexError("t").exit_code, 1)
        self.assertEqual(cortex.WorkflowExecutionError("t").exit_code, 1)
        self.assertEqual(cortex.CapabilityViolationError("t").exit_code, 2)
        self.assertEqual(cortex.ManifestError("t").exit_code, 3)


class TestPublicAPIDocstrings(unittest.TestCase):
    """All public symbols must have complete docstrings."""

    def test_all_public_symbols_have_docstrings(self) -> None:
        """Every symbol in cortex.__all__ must have a non-empty docstring."""
        for symbol_name in sorted(cortex.__all__):
            with self.subTest(symbol=symbol_name):
                obj = getattr(cortex, symbol_name)
                doc = getattr(obj, "__doc__", None)
                self.assertTrue(
                    doc and len(doc.strip()) > 0,
                    f"Public symbol '{symbol_name}' is missing a docstring",
                )


class TestPublicAPIBoundaryEnforcement(unittest.TestCase):
    """Validate that internal modules do not leak into the public API."""

    def test_no_private_symbols_in_all(self) -> None:
        """No underscore-prefixed symbols should appear in cortex.__all__."""
        private = [s for s in cortex.__all__ if s.startswith("_")]
        self.assertEqual(
            private,
            [],
            f"Private symbols leaked into cortex.__all__: {private}",
        )

    def test_no_kernel_symbols_in_all(self) -> None:
        """No 'kernel' or 'tools' module objects should appear in cortex.__all__."""
        import types
        for symbol_name in cortex.__all__:
            with self.subTest(symbol=symbol_name):
                obj = getattr(cortex, symbol_name)
                if isinstance(obj, types.ModuleType):
                    self.fail(
                        f"Module object '{symbol_name}' leaked into cortex.__all__"
                    )

    def test_internal_packages_have_empty_all(self) -> None:
        """All internal subpackages must define __all__ = [] to block wildcard imports."""
        for pkg_path in INTERNAL_PACKAGES:
            with self.subTest(package=pkg_path):
                mod = importlib.import_module(pkg_path)
                pkg_all = getattr(mod, "__all__", None)
                self.assertIsNotNone(
                    pkg_all,
                    f"Internal package '{pkg_path}' does not define __all__",
                )
                self.assertEqual(
                    list(pkg_all),  # type: ignore[arg-type]
                    [],
                    f"Internal package '{pkg_path}' has non-empty __all__: {pkg_all}",
                )

    def test_override_is_callable(self) -> None:
        """The override compatibility shim must be a callable decorator."""
        self.assertTrue(
            callable(cortex.override),
            "cortex.override must be callable",
        )

    def test_symbol_count_is_exact(self) -> None:
        """The public API must have exactly 21 symbols."""
        self.assertEqual(
            len(cortex.__all__),
            21,
            f"Expected 21 public symbols, got {len(cortex.__all__)}",
        )


if __name__ == "__main__":
    _ = unittest.main()
