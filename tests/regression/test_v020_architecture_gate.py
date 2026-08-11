"""
v0.2.0 Regression: Architecture Research Gate & Synthesis (Post Issue #12)

Validates:
- Architecture Gate synthesis execution across 5 architectural questions
- Recommended Tiered Hybrid Isolation Model decision
- Public API surface boundary freeze (len(cortex.__all__) == 21)
"""

import unittest

import cortex
from cortex._research.architecture_gate import generate_architecture_gate_synthesis


class TestArchitectureResearchGate(unittest.TestCase):
    """Regression test suite for the Architecture Research Gate."""

    def test_public_api_symbols_frozen_at_21(self) -> None:
        """Public API surface must remain locked at exactly 21 symbols."""
        self.assertEqual(len(cortex.__all__), 21)
        self.assertNotIn("_research", cortex.__all__)

    def test_internal_package_has_empty_all(self) -> None:
        """cortex._research subpackage must define __all__ = []."""
        import cortex._research
        self.assertEqual(cortex._research.__all__, [])

    def test_architecture_gate_synthesis_decision(self) -> None:
        """Executes Architecture Gate synthesis and validates decision outcomes."""
        res = generate_architecture_gate_synthesis()

        self.assertIn("synthesis", res)
        self.assertIn("gate_decision", res)

        synthesis = res["synthesis"]
        gate = res["gate_decision"]

        # Question 1
        self.assertEqual(synthesis["q1_recovery_targets"]["authoritative_source"], "EventStore append-only journal log")

        # Question 3
        self.assertIn("IN_DOUBT", synthesis["q3_side_effect_semantics"]["chosen_contract_option"])

        # Question 5
        self.assertIn("Tiered Hybrid Isolation", synthesis["q5_architectural_topology_comparison"]["recommended_architecture"])

        # Gate decision
        self.assertTrue(gate["architecture_gate_passed"])
        self.assertTrue(gate["issue_13_authorized"])


if __name__ == "__main__":
    _ = unittest.main()
