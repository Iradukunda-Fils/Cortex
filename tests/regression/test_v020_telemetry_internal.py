"""
v0.2.0 Regression: Internal Telemetry & Benchmark Verification (Issue #10)

Validates:
- Internal telemetry model serialization & statistical calculations
- Telemetry non-intrusiveness (preserves workflow state, event ordering, lineage)
- Public API boundary freeze (len(cortex.__all__) == 21, no internal telemetry exports)
"""

import unittest

import cortex
from cortex import CortexClient, WorkflowState
from cortex._telemetry.benchmark import BaselinePlannerPlugin, run_benchmark_suite
from cortex._telemetry.collector import TelemetryCollector
from cortex._telemetry.models import calculate_quantiles


class TestInternalTelemetryHarness(unittest.TestCase):
    """Regression test suite for private internal telemetry module."""

    def test_public_api_symbols_frozen_at_21(self) -> None:
        """Public API surface must remain locked at exactly 21 symbols."""
        self.assertEqual(len(cortex.__all__), 21)
        self.assertNotIn("_telemetry", cortex.__all__)
        self.assertNotIn("TelemetryCollector", cortex.__all__)

    def test_internal_package_has_empty_all(self) -> None:
        """cortex._telemetry subpackage must define __all__ = []."""
        import cortex._telemetry

        self.assertEqual(cortex._telemetry.__all__, [])

    def test_calculate_quantiles_accuracy(self) -> None:
        """Statistical quantiles (P50, P95, P99, mean, min, max, stdev) calculation accuracy."""
        samples = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        p50, p95, p99, mean_v, min_v, max_v, stdev_v = calculate_quantiles(samples)

        self.assertAlmostEqual(p50, 5.5, delta=0.5)
        self.assertAlmostEqual(p95, 9.55, delta=0.5)
        self.assertAlmostEqual(p99, 9.91, delta=0.5)
        self.assertEqual(min_v, 1.0)
        self.assertEqual(max_v, 10.0)
        self.assertAlmostEqual(mean_v, 5.5)

    def test_telemetry_collector_is_non_intrusive(self) -> None:
        """Collector observes execution without mutating state or event streams."""
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(BaselinePlannerPlugin())
        wf = client.create_workflow(name="test_wf", goal="Test non-intrusiveness")

        collector = TelemetryCollector(client)
        executed = client.run_workflow(wf)
        rec = collector.collect_workflow_metrics(executed, 1000000, 5000000)

        self.assertEqual(executed.state, WorkflowState.COMPLETED)
        self.assertEqual(rec.final_state, "COMPLETED")
        self.assertEqual(rec.event_count, 2)
        self.assertEqual(rec.verification_failed_count, 0)
        self.assertTrue(rec.lineage_intact)

    def test_benchmark_suite_runs_n_samples(self) -> None:
        """Benchmark suite runs N samples per workload and outputs valid summary stats."""
        res = run_benchmark_suite(sample_count=5)

        self.assertIn("workload_a", res)
        self.assertIn("workload_b", res)
        self.assertIn("workload_c", res)

        wa = res["workload_a"]
        self.assertEqual(wa["sample_count"], 5)
        self.assertGreater(wa["p50_ms"], 0.0)
        self.assertEqual(wa["event_count"], 2)


if __name__ == "__main__":
    _ = unittest.main()
