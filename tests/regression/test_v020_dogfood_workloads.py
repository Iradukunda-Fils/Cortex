"""
v0.2.0 Regression: Dogfood Workload Profile Tests

Validates that the dogfood harness executes all 5 controlled synthetic
workload profiles correctly. Tests behavior and contracts, NOT benchmark timing.
"""

import os
import shutil
import tempfile
import unittest

from examples.repo_auditor.dogfood_harness import WORKLOAD_PROFILES, run_profile
from examples.repo_auditor.plugins.configurable_planner import (
    MAX_STEP_COUNT,
    MIN_STEP_COUNT,
    ConfigurablePlannerPlugin,
)


class TestDogfoodWorkloads(unittest.TestCase):
    """Regression tests for controlled synthetic workload execution."""

    test_dir: str = ""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp(prefix="cortex_dogfood_test_")

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_minimal_profile_completes(self) -> None:
        """Minimal profile (3 steps) completes with proven replay equivalence."""
        profile = WORKLOAD_PROFILES[0]
        result = run_profile(profile, self.test_dir)
        self.assertEqual(result.profile_name, "minimal")
        self.assertEqual(result.workflow_state, "COMPLETED")
        self.assertTrue(result.replay.proven_equivalent)
        self.assertGreater(result.events.total, 0)

    def test_standard_profile_completes(self) -> None:
        """Standard profile (10 steps) completes with proven replay equivalence."""
        profile = WORKLOAD_PROFILES[1]
        result = run_profile(profile, self.test_dir)
        self.assertEqual(result.profile_name, "standard")
        self.assertEqual(result.workflow_state, "COMPLETED")
        self.assertTrue(result.replay.proven_equivalent)

    def test_large_profile_completes(self) -> None:
        """Large profile (50 steps) completes with proven replay equivalence."""
        profile = WORKLOAD_PROFILES[2]
        result = run_profile(profile, self.test_dir)
        self.assertEqual(result.profile_name, "large")
        self.assertEqual(result.workflow_state, "COMPLETED")
        self.assertTrue(result.replay.proven_equivalent)

    def test_stress_profile_completes(self) -> None:
        """Stress profile (200 steps) completes with proven replay equivalence."""
        profile = WORKLOAD_PROFILES[3]
        result = run_profile(profile, self.test_dir)
        self.assertEqual(result.profile_name, "stress")
        self.assertEqual(result.workflow_state, "COMPLETED")
        self.assertTrue(result.replay.proven_equivalent)

    def test_violation_profile_fails(self) -> None:
        """Violation profile triggers FAILED state with capability violations."""
        profile = WORKLOAD_PROFILES[4]
        result = run_profile(profile, self.test_dir)
        self.assertEqual(result.profile_name, "violation")
        self.assertEqual(result.workflow_state, "FAILED")
        self.assertGreater(result.capabilities.violation_count, 0)

    def test_event_count_scales_with_steps(self) -> None:
        """Larger workloads produce proportionally more events."""
        minimal = run_profile(WORKLOAD_PROFILES[0], self.test_dir)
        standard = run_profile(WORKLOAD_PROFILES[1], self.test_dir)
        self.assertGreater(standard.events.total, minimal.events.total)

    def test_trace_files_created(self) -> None:
        """Each profile generates a trace file on disk."""
        for profile in WORKLOAD_PROFILES:
            name = str(profile["name"])
            with self.subTest(profile=name):
                _ = run_profile(profile, self.test_dir)
                trace_path = os.path.join(self.test_dir, f"trace_{name}.json")
                self.assertTrue(os.path.exists(trace_path))

    def test_command_events_match_step_count(self) -> None:
        """Non-violation profiles emit CommandIssuedEvent count matching step_count."""
        for profile in WORKLOAD_PROFILES:
            if bool(profile["violation"]):
                continue
            name = str(profile["name"])
            steps = int(str(profile["steps"]))
            with self.subTest(profile=name):
                result = run_profile(profile, self.test_dir)
                self.assertEqual(result.events.command, steps)

    def test_replay_count_matches_event_count(self) -> None:
        """Replay event count must match original for non-violation profiles."""
        for profile in WORKLOAD_PROFILES:
            if bool(profile["violation"]):
                continue
            name = str(profile["name"])
            with self.subTest(profile=name):
                result = run_profile(profile, self.test_dir)
                self.assertEqual(result.replay.events_replayed, result.events.total)

    def test_all_profiles_have_positive_timing(self) -> None:
        """All profiles must report positive total execution time."""
        for profile in WORKLOAD_PROFILES:
            name = str(profile["name"])
            with self.subTest(profile=name):
                result = run_profile(profile, self.test_dir)
                self.assertGreater(result.timings.total_s, 0)

    def test_workload_type_is_synthetic(self) -> None:
        """All profiles must report workload_type as 'synthetic'."""
        result = run_profile(WORKLOAD_PROFILES[0], self.test_dir)
        self.assertEqual(result.workload_type, "synthetic")

    def test_environment_metadata_populated(self) -> None:
        """Environment metadata must be populated."""
        result = run_profile(WORKLOAD_PROFILES[0], self.test_dir)
        self.assertTrue(len(result.environment.python_version) > 0)
        self.assertEqual(result.environment.cortex_version, "0.2.0")
        self.assertTrue(len(result.environment.os_name) > 0)


class TestConfigurablePlannerValidation(unittest.TestCase):
    """Validate input rejection for invalid workload configurations."""

    def test_zero_steps_rejected(self) -> None:
        """Step count of 0 must raise ValueError."""
        with self.assertRaises(ValueError):
            ConfigurablePlannerPlugin(step_count=0)

    def test_negative_steps_rejected(self) -> None:
        """Negative step count must raise ValueError."""
        with self.assertRaises(ValueError):
            ConfigurablePlannerPlugin(step_count=-5)

    def test_exceeds_max_rejected(self) -> None:
        """Step count exceeding MAX_STEP_COUNT must raise ValueError."""
        with self.assertRaises(ValueError):
            ConfigurablePlannerPlugin(step_count=MAX_STEP_COUNT + 1)

    def test_min_steps_accepted(self) -> None:
        """Minimum valid step count must be accepted."""
        plugin = ConfigurablePlannerPlugin(step_count=MIN_STEP_COUNT)
        self.assertEqual(plugin.step_count, MIN_STEP_COUNT)

    def test_valid_steps_accepted(self) -> None:
        """Normal step counts must be accepted."""
        plugin = ConfigurablePlannerPlugin(step_count=50)
        self.assertEqual(plugin.step_count, 50)


if __name__ == "__main__":
    _ = unittest.main()
