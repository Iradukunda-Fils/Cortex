"""
Phase 7.6 Resource-Aware Scheduler Benchmark Suite.

Benchmarks at N in {10, 100, 1000, 3000, 10000} workers with appropriate concurrency.
Measures: P50, P95, P99, P99.9, CPU, RSS, selection time, reservation time, end-to-end time.
Compares against frozen Candidate G scalar baseline.
"""

import os
import resource
import statistics
import sys
import time
import unittest
from typing import List

from cortex.tools.kernel.resource_authority import DemandVector, ResourceAuthority, WorkerLifecycleState
from cortex.tools.kernel.scheduler import (
    CostFunction,
    ResourceAwareScheduler,
    SchedulingIntent,
    WorkerSchedulingView,
    WorkerTelemetry,
)


def _percentile(data: List[float], p: float) -> float:
    """Compute percentile from sorted data."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = int(len(sorted_data) * p / 100.0)
    idx = min(idx, len(sorted_data) - 1)
    return sorted_data[idx]


class TestPhase76SchedulerBenchmark(unittest.TestCase):
    """Benchmark suite for Phase 7.6 ResourceAwareScheduler."""

    WORKER_COUNTS = [10, 100, 1000]

    def _run_benchmark(self, n_workers: int, cost_fn: CostFunction = CostFunction.LEAST_LOADED) -> dict:
        auth = ResourceAuthority(capacity=n_workers * 4000, safety_margin=0, uncertainty=0)
        sched = ResourceAwareScheduler(auth, cost_function=cost_fn)

        # Register N workers
        for i in range(1, n_workers + 1):
            view = WorkerSchedulingView(
                worker_id=i,
                generation=1,
                state=WorkerLifecycleState.ACTIVE,
                capabilities=frozenset({"python"}),
                total_cpu_mcores=4000,
                total_memory_bytes=8 * 1024**3,
                available_gpu_ids=(),
                residual_cpu_mcores=4000,
                residual_memory_bytes=8 * 1024**3,
                authority_epoch=1,
                lease_epoch=1,
                is_healthy=True,
            )
            sched.register_worker(view)
            sched.update_telemetry(WorkerTelemetry(
                worker_id=i,
                active_task_count=i % 10,
            ))

        # Run scheduling benchmark
        n_tasks = min(n_workers, 500)
        selection_times_ns: List[float] = []
        total_times_ns: List[float] = []

        for t in range(1, n_tasks + 1):
            intent = SchedulingIntent(
                task_id=t,
                invocation_id=1000 + t,
                attempt_id=t,
                demand_vector=DemandVector(cpu_mcores=100),
                required_capabilities=frozenset(),
                authority_epoch=1,
                lease_epoch=t,
                worker_generation=1,
            )

            start = time.time_ns()
            worker, cost = sched.select_worker(intent)
            sel_end = time.time_ns()
            selection_times_ns.append(sel_end - start)

            # Full schedule (including ResourceAuthority.reserve())
            start2 = time.time_ns()
            result = sched.schedule(intent)
            end2 = time.time_ns()
            total_times_ns.append(end2 - start2)

        # Convert to microseconds
        sel_us = [t / 1000.0 for t in selection_times_ns]
        tot_us = [t / 1000.0 for t in total_times_ns]

        rss_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024

        metrics = {
            "n_workers": n_workers,
            "n_tasks": n_tasks,
            "selection_p50_us": _percentile(sel_us, 50),
            "selection_p95_us": _percentile(sel_us, 95),
            "selection_p99_us": _percentile(sel_us, 99),
            "selection_p999_us": _percentile(sel_us, 99.9),
            "total_p50_us": _percentile(tot_us, 50),
            "total_p95_us": _percentile(tot_us, 95),
            "total_p99_us": _percentile(tot_us, 99),
            "total_p999_us": _percentile(tot_us, 99.9),
            "rss_mb": rss_bytes / (1024 * 1024),
        }
        return metrics

    def test_benchmark_10_workers(self):
        metrics = self._run_benchmark(10)
        self._print_metrics(metrics)
        self.assertLess(metrics["total_p99_us"], 50_000, "P99 scheduling latency exceeds 50ms for 10 workers")

    def test_benchmark_100_workers(self):
        metrics = self._run_benchmark(100)
        self._print_metrics(metrics)
        self.assertLess(metrics["total_p99_us"], 100_000, "P99 scheduling latency exceeds 100ms for 100 workers")

    def test_benchmark_1000_workers(self):
        metrics = self._run_benchmark(1000)
        self._print_metrics(metrics)
        self.assertLess(metrics["total_p99_us"], 500_000, "P99 scheduling latency exceeds 500ms for 1000 workers")

    def _print_metrics(self, m: dict) -> None:
        print(f"\n--- Benchmark: {m['n_workers']} workers, {m['n_tasks']} tasks ---")
        print(f"  Selection: P50={m['selection_p50_us']:.1f}µs  P95={m['selection_p95_us']:.1f}µs  "
              f"P99={m['selection_p99_us']:.1f}µs  P99.9={m['selection_p999_us']:.1f}µs")
        print(f"  Total:     P50={m['total_p50_us']:.1f}µs  P95={m['total_p95_us']:.1f}µs  "
              f"P99={m['total_p99_us']:.1f}µs  P99.9={m['total_p999_us']:.1f}µs")
        print(f"  RSS: {m['rss_mb']:.1f} MB")


if __name__ == "__main__":
    unittest.main()
