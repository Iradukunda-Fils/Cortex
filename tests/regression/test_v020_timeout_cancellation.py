"""
v0.2.0 Regression: Workflow Timeout & Cancellation Semantics (Issue #12)

Validates:
- Scenarios A through G resource and cancellation research suite execution
- Cooperative vs non-cooperative execution characterization
- Event journal lineage preservation post-cancellation
- Subsequent workflow isolation and public API boundary freeze (len(cortex.__all__) == 21)
"""

import unittest

import cortex
from cortex._research.timeout_cancellation import execute_timeout_cancellation_research


class TestTimeoutCancellationResearchSuite(unittest.TestCase):
    """Regression test suite for Issue #12 workflow timeout and cancellation semantics."""

    def test_public_api_symbols_frozen_at_21(self) -> None:
        """Public API surface must remain locked at exactly 21 symbols."""
        self.assertEqual(len(cortex.__all__), 21)
        self.assertNotIn("_research", cortex.__all__)

    def test_internal_package_has_empty_all(self) -> None:
        """cortex._research subpackage must define __all__ = []."""
        import cortex._research

        self.assertEqual(cortex._research.__all__, [])

    def test_scenarios_a_through_g_execution(self) -> None:
        """Executes Scenarios A through G and asserts all empirical invariants."""
        res = execute_timeout_cancellation_research()

        self.assertIn("scenarios", res)
        scenarios = res["scenarios"]

        # Scenario A
        self.assertTrue(scenarios["scenario_a"]["zero_journal_pollution"])
        self.assertEqual(scenarios["scenario_a"]["final_state"], "FAILED")

        # Scenario B
        self.assertTrue(scenarios["scenario_b"]["stage_1_events_preserved"])
        self.assertTrue(scenarios["scenario_b"]["downstream_stage_3_halted"])
        self.assertTrue(scenarios["scenario_b"]["timeout_policy_event_recorded"])

        # Scenario C
        self.assertTrue(scenarios["scenario_c"]["cooperative_execution_succeded"])

        # Scenario D
        self.assertGreater(scenarios["scenario_d"]["main_thread_blocked_sec"], 0.0)

        # Scenario E
        self.assertTrue(scenarios["scenario_e"]["lineage_graph_intact"])
        self.assertTrue(scenarios["scenario_e"]["pre_cancellation_events_replayable"])

        # Scenario F
        self.assertTrue(scenarios["scenario_f"]["subsequent_workflow_healthy"])

        # Scenario G
        self.assertTrue(scenarios["scenario_g"]["deterministic_cancellation"])
        self.assertEqual(scenarios["scenario_g"]["iteration_count"], 10)


if __name__ == "__main__":
    _ = unittest.main()
