"""
v0.2.0 Regression: Plugin Crash & Failure Semantics (Issue #11)

Validates:
- Scenarios A through F fault boundary research suite execution
- Exception trapping & VerificationResultEvent emission
- Host process survival and clean subsequent workflow isolation
- Public API surface boundary freeze (len(cortex.__all__) == 21)
"""

import unittest

import cortex
from cortex._research.crash_semantics import execute_crash_semantics_research


class TestCrashSemanticsResearchSuite(unittest.TestCase):
    """Regression test suite for Issue #11 plugin crash and failure semantics."""

    def test_public_api_symbols_frozen_at_21(self) -> None:
        """Public API surface must remain locked at exactly 21 symbols."""
        self.assertEqual(len(cortex.__all__), 21)
        self.assertNotIn("_research", cortex.__all__)

    def test_internal_package_has_empty_all(self) -> None:
        """cortex._research subpackage must define __all__ = []."""
        import cortex._research
        self.assertEqual(cortex._research.__all__, [])

    def test_scenarios_a_through_f_execution(self) -> None:
        """Executes Scenarios A through F and asserts all empirical invariants."""
        res = execute_crash_semantics_research()

        self.assertIn("scenarios", res)
        scenarios = res["scenarios"]

        # Scenario A
        self.assertTrue(scenarios["scenario_a"]["host_survived"])
        self.assertEqual(scenarios["scenario_a"]["final_state"], "FAILED")
        self.assertTrue(scenarios["scenario_a"]["verification_failure_emitted"])

        # Scenario B
        self.assertTrue(scenarios["scenario_b"]["host_survived"])
        self.assertEqual(scenarios["scenario_b"]["final_state"], "FAILED")
        self.assertEqual(scenarios["scenario_b"]["error_type"], "CapabilityViolationError")

        # Scenario C
        self.assertTrue(scenarios["scenario_c"]["host_survived"])
        self.assertEqual(scenarios["scenario_c"]["final_state"], "FAILED")
        self.assertEqual(scenarios["scenario_c"]["registration_state"], "REJECTED")

        # Scenario D
        self.assertTrue(scenarios["scenario_d"]["host_survived"])
        self.assertTrue(scenarios["scenario_d"]["stage_a_produced_events"])
        self.assertFalse(scenarios["scenario_d"]["stage_c_executed"])
        self.assertEqual(scenarios["scenario_d"]["final_state"], "FAILED")

        # Scenario E
        self.assertTrue(scenarios["scenario_e"]["host_survived"])
        self.assertEqual(scenarios["scenario_e"]["failure_events_recorded"], 2)

        # Scenario F
        self.assertTrue(scenarios["scenario_f"]["host_survived"])
        self.assertEqual(scenarios["scenario_f"]["workflow_1_final_state"], "FAILED")
        self.assertEqual(scenarios["scenario_f"]["workflow_2_final_state"], "COMPLETED")
        self.assertTrue(scenarios["scenario_f"]["subsequent_workflow_isolated"])


if __name__ == "__main__":
    _ = unittest.main()
