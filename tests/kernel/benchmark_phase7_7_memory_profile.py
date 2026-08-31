"""
Phase 7.7 Memory Profiling Benchmark.

Measures per-tier memory breakdown to distinguish:
  - Process RSS (ru_maxrss)
  - Scheduler state incremental memory (sys.getsizeof on engine internals)
  - Per-worker incremental cost

Reports at each tier boundary: N=0 (baseline), 10, 100, 1000.
"""

import gc
import os
import resource
import sys
import time
from typing import Dict, List

from cortex.tools.kernel.distributed_scheduler import (
    DistributedPlacementEngine,
    DistributedWorkerView,
    GlobalGPUIdentity,
    GlobalWorkerIdentity,
)
from cortex.tools.kernel.resource_authority import DemandVector, ResourceAuthority, WorkerLifecycleState
from cortex.tools.kernel.scheduler import CostFunction, SchedulingIntent, WorkerTelemetry


def get_rss_mb() -> float:
    """Get current process RSS in MB via /proc/self/status (Linux)."""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0  # kB -> MB
    except Exception:
        pass
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def measure_engine_object_size(engine: DistributedPlacementEngine) -> int:
    """Approximate memory of the engine's worker registry dict."""
    total = sys.getsizeof(engine._workers)
    for k, v in engine._workers.items():
        total += sys.getsizeof(k) + sys.getsizeof(v)
    return total


def run_memory_profile():
    tiers = [0, 10, 100, 1000]
    n_nodes = 10

    print("=" * 80)
    print("Phase 7.7 Memory Profiling Benchmark")
    print("=" * 80)
    print(f"{'Tier':>8} | {'Workers':>8} | {'RSS_cur(MB)':>12} | {'RSS_max(MB)':>12} | "
          f"{'Engine(bytes)':>14} | {'Per-Worker(bytes)':>18}")
    print("-" * 80)

    gc.collect()
    rss_baseline = get_rss_mb()
    rss_max_baseline = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 / (1024 * 1024)

    # Baseline: no engine
    print(f"{'base':>8} | {'0':>8} | {rss_baseline:>12.2f} | {rss_max_baseline:>12.2f} | "
          f"{'N/A':>14} | {'N/A':>18}")

    authorities: Dict[str, ResourceAuthority] = {}
    for n in range(1, n_nodes + 1):
        authorities[f"node-{n}"] = ResourceAuthority(capacity=100000, safety_margin=0, uncertainty=0)

    engine = DistributedPlacementEngine(node_authorities=authorities)

    prev_engine_size = 0
    prev_workers = 0

    for tier_target in tiers:
        if tier_target == 0:
            gc.collect()
            rss_now = get_rss_mb()
            rss_max = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 / (1024 * 1024)
            eng_size = measure_engine_object_size(engine)
            print(f"{'init':>8} | {0:>8} | {rss_now:>12.2f} | {rss_max:>12.2f} | "
                  f"{eng_size:>14} | {'N/A':>18}")
            prev_engine_size = eng_size
            continue

        # Add workers up to tier_target
        for i in range(prev_workers + 1, tier_target + 1):
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

        gc.collect()
        rss_now = get_rss_mb()
        rss_max = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 / (1024 * 1024)
        eng_size = measure_engine_object_size(engine)
        added = tier_target - prev_workers
        delta_bytes = eng_size - prev_engine_size
        per_worker = delta_bytes / added if added > 0 else 0

        print(f"{tier_target:>8} | {tier_target:>8} | {rss_now:>12.2f} | {rss_max:>12.2f} | "
              f"{eng_size:>14} | {per_worker:>18.1f}")

        prev_engine_size = eng_size
        prev_workers = tier_target

    print("=" * 80)
    print()
    print("Measurement notes:")
    print("  - RSS_cur: Current VmRSS from /proc/self/status (Linux)")
    print("  - RSS_max: Peak ru_maxrss from getrusage (includes test harness, interpreter, imports)")
    print("  - Engine(bytes): sys.getsizeof(engine._workers) + keys + values")
    print("  - Per-Worker(bytes): incremental engine dict cost per added worker")
    print("  - All measurements in single OS process, single thread, logical simulation only")
    print("  - Physical nodes: 0 (all workers are logical objects in process memory)")
    print("  - OS processes: 1")
    print("  - Threads: 1 (benchmark is single-threaded)")


if __name__ == "__main__":
    run_memory_profile()
