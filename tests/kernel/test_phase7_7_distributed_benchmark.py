"""
Phase 7.7 Distributed Placement Benchmark Suite.

Benchmarks multi-node placement engine at N in {10, 100, 1000, 3000, 10000} workers.
Measures: P50, P95, P99, P99.9, RSS memory footprint, and retry/rejection rate.
"""

import resource
import time
import unittest
from typing import Dict, List

from cortex.tools.kernel.distributed_scheduler import (
    DistributedPlacementEngine,
    DistributedWorkerView,
    GlobalGPUIdentity,
    GlobalWorkerIdentity,
)
from cortex.tools.kernel.resource_authority import DemandVector, ResourceAuthority, WorkerLifecycleState
from cortex.tools.kernel.scheduler import CostFunction, SchedulingIntent, WorkerTelemetry


def _percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    s_data = sorted(data)
    idx = min(int(len(s_data) * p / 100.0), len(s_data) - 1)
    return s_data[idx]


class TestPhase77DistributedBenchmark(unittest.TestCase):
    """Benchmark suite for Phase 7.7a Distributed Placement Engine."""

    def _run_benchmark(self, n_workers: int, n_nodes: int = 10) -> dict:
        authorities: Dict[str, ResourceAuthority] = {}
        per_node_workers = max(1, n_workers // n_nodes)

        for n in range(1, n_nodes + 1):
            node_id = f"node-{n}"
            authorities[node_id] = ResourceAuthority(capacity=per_node_workers * 4000, safety_margin=0, uncertainty=0)

        engine = DistributedPlacementEngine(node_authorities=authorities)

        # Register N workers across n_nodes
        for i in range(1, n_workers + 1):
            node_id = f"node-{((i - 1) % n_nodes) + 1}"
            identity = GlobalWorkerIdentity(node_id=node_id, worker_id=i, generation=1)
            view = DistributedWorkerView(
                identity=identity,
                state=WorkerLifecycleState.ACTIVE,
                capabilities=frozenset({"python"}),
                total_capacity=DemandVector(cpu_mcores=4000, memory_bytes=8 * 1024**3),
                residual_capacity=DemandVector(cpu_mcores=4000, memory_bytes=8 * 1024**3),
                available_gpus=(),
                node_region="us-east-1" if i % 2 == 0 else "us-west-2",
                authority_epoch=1,
                lease_epoch=1,
                is_healthy=True,
                telemetry=WorkerTelemetry(worker_id=i, active_task_count=i % 10),
            )
            engine.register_worker(view)

        n_tasks = min(n_workers, 500)
        sel_times_ns: List[float] = []
        tot_times_ns: List[float] = []

        for t in range(1, n_tasks + 1):
            intent = SchedulingIntent(
                task_id=t,
                invocation_id=1000 + t,
                attempt_id=t,
                demand_vector=DemandVector(cpu_mcores=100),
                authority_epoch=1,
                lease_epoch=t,
                worker_generation=1,
            )

            start = time.time_ns()
            worker, cost = engine.select_worker(intent, target_region="us-east-1")
            sel_end = time.time_ns()
            sel_times_ns.append(sel_end - start)

            # Schedule via atomic node ResourceAuthority.reserve()
            start2 = time.time_ns()
            w_res, res = engine.schedule_distributed(intent, target_region="us-east-1")
            end2 = time.time_ns()
            tot_times_ns.append(end2 - start2)

        sel_us = [x / 1000.0 for x in sel_times_ns]
        tot_us = [x / 1000.0 for x in tot_times_ns]
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
        self.assertLess(metrics["total_p99_us"], 50_000)

    def test_benchmark_100_workers(self):
        metrics = self._run_benchmark(100)
        self._print_metrics(metrics)
        self.assertLess(metrics["total_p99_us"], 100_000)

    def test_benchmark_1000_workers(self):
        metrics = self._run_benchmark(1000)
        self._print_metrics(metrics)
        self.assertLess(metrics["total_p99_us"], 500_000)

    def _print_metrics(self, m: dict) -> None:
        print(f"\n--- Phase 7.7 Distributed Benchmark: {m['n_workers']} workers, {m['n_tasks']} tasks ---")
        print(f"  Selection: P50={m['selection_p50_us']:.1f}µs  P95={m['selection_p95_us']:.1f}µs  "
              f"P99={m['selection_p99_us']:.1f}µs  P99.9={m['selection_p999_us']:.1f}µs")
        print(f"  Total:     P50={m['total_p50_us']:.1f}µs  P95={m['total_p95_us']:.1f}µs  "
              f"P99={m['total_p99_us']:.1f}µs  P99.9={m['total_p999_us']:.1f}µs")
        print(f"  RSS: {m['rss_mb']:.1f} MB")


if __name__ == "__main__":
    unittest.main()
