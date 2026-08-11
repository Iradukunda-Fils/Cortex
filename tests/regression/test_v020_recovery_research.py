"""
v0.2.0 Regression: Restart, Recovery & Side-Effect Research (Issue #13)

Validates:
- Experiments A through E research suite execution with child subprocess isolation
- Memory loss on process termination characterization
- Side-effect crash point ambiguity (B1, B2, B3)
- Idempotency key deduplication proof
- Public API surface boundary freeze (len(cortex.__all__) == 21)
"""

import unittest

import cortex
from cortex._research.recovery import execute_recovery_research_suite


class TestRecoveryResearchSuite(unittest.TestCase):
    """Regression test suite for Issue #13 recovery and side-effect research."""

    def test_public_api_symbols_frozen_at_21(self) -> None:
        """Public API surface must remain locked at exactly 21 symbols."""
        self.assertEqual(len(cortex.__all__), 21)
        self.assertNotIn("_research", cortex.__all__)

    def test_internal_package_has_empty_all(self) -> None:
        """cortex._research subpackage must define __all__ = []."""
        import cortex._research
        self.assertEqual(cortex._research.__all__, [])

    def test_experiments_a_through_e_execution(self) -> None:
        """Executes Experiments A through E and asserts empirical invariants."""
        res = execute_recovery_research_suite()

        self.assertIn("experiments", res)
        self.assertIn("five_core_empirical_questions", res)

        exp = res["experiments"]

        # Experiment A
        self.assertFalse(exp["experiment_a"]["in_memory_state_survived"])

        # Experiment B
        self.assertEqual(exp["experiment_b"]["b1_pre_execution"]["side_effect_mutations"], 0)
        self.assertEqual(exp["experiment_b"]["b2_mid_execution"]["side_effect_mutations"], 1)
        self.assertEqual(exp["experiment_b"]["b3_post_execution"]["side_effect_mutations"], 1)

        # Experiment C
        self.assertTrue(exp["experiment_c"]["duplicate_reproduced"])
        self.assertTrue(exp["experiment_c"]["idempotency_eliminates_duplication"])

        # Experiment D & E
        self.assertIn("RECOVERABLE", exp["experiment_d"]["taxonomy_rules"])

        # Summary
        self.assertTrue(res["summary"]["research_gate_passed"])


if __name__ == "__main__":
    _ = unittest.main()
