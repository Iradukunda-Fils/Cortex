"""
Issue #50.d / #51 Standardization & Lock Attribution Benchmark Suite

Comprehensive Metadata Recording:
- Environment: Hardware, Python Version, Clock Source, GC State
- Lock Attribution: T_wait (acquisition queue latency) vs T_hold (critical section duration)
- Architecture Prototype: Immutable Snapshot Read View (V = f(S_A)) vs Global RLock
- Scales: N in {10, 100, 1,000, 10,000} with |W_c| tracking
- Multi-Threaded Concurrency: C in {1, 2, 4, 8, 16, 32, 64}
"""

from __future__ import annotations

import concurrent.futures
import gc
import json
import os
import platform
import sys
import time
import tracemalloc
import unittest
from dataclasses import asdict, dataclass
from typing import List, Tuple

from cortex.tools.kernel.load_balancer import (
    DEFAULT_INITIAL_EPOCH,
    ProductionDynamicLoadBalancer,
)


@dataclass
class SystemMetadata:
    system_os: str
    architecture: str
    python_version: str
    logical_cpus: int
    clock_source: str
    gc_enabled: bool


@dataclass
class LockAttributionMetrics:
    mode: str
    scale_n: int
    w_c_subset_size: int
    thread_count: int
    ops_total: int
    throughput_ops_per_sec: float
    total_wall_time_ms: float
    p50_latency_us: float
    p95_latency_us: float
    p99_latency_us: float
    p999_latency_us: float
    t_wait_p50_us: float
    t_wait_p99_us: float
    t_hold_p50_us: float
    t_hold_p99_us: float
    p_wait_contention_pct: float
    peak_memory_kb: float


class TestSchedulerBenchmarkSuite(unittest.TestCase):
    """Issue #50.d Multi-Scale & Snapshot Read-View Concurrency Benchmark Suite."""

    def setUp(self) -> None:
        gc.collect()
        tracemalloc.start()

    def tearDown(self) -> None:
        tracemalloc.stop()

    def _get_system_metadata(self) -> SystemMetadata:
        return SystemMetadata(
            system_os=f"{platform.system()} {platform.release()}",
            architecture=platform.machine(),
            python_version=sys.version.split()[0],
            logical_cpus=os.cpu_count() or 1,
            clock_source="time.perf_counter_ns",
            gc_enabled=gc.isenabled(),
        )

    def _profile_lock_attribution(
        self,
        scale_n: int,
        num_threads: int,
        use_snapshot: bool,
        ops_per_thread: int = 100,
        warmup_ops: int = 20,
    ) -> LockAttributionMetrics:
        lb = ProductionDynamicLoadBalancer(
            max_registered_workers=scale_n + 500,
            max_quarantine_records=scale_n + 500,
        )

        capabilities_pool = ["inference", "embedding", "translation", "summarization", "vision"]
        for i in range(scale_n):
            cap = capabilities_pool[i % len(capabilities_pool)]
            lb.register_worker(worker_id=f"worker_{i}", capabilities={cap}, max_concurrency=100)

        w_c_subset_size = scale_n // len(capabilities_pool)
        now_ms = int(time.time() * 1000)

        # Warmup phase
        for i in range(warmup_ops):
            cap = capabilities_pool[i % len(capabilities_pool)]
            target_w = lb.select_target_worker(cap, now_ms, use_snapshot_read_view=use_snapshot)
            lb.assign_execution(target_w, f"warmup_{i}", DEFAULT_INITIAL_EPOCH, now_ms)

        # Enforce Invariant I_9 post warmup
        lb.assert_capability_index_consistency()

        thread_latencies_us: List[float] = []
        t_waits_us: List[float] = []
        t_holds_us: List[float] = []
        contended_count = 0

        def worker_task(thread_id: int) -> List[Tuple[float, float, float, bool]]:
            local_samples = []
            for i in range(ops_per_thread):
                cap = capabilities_pool[(thread_id + i) % len(capabilities_pool)]
                inv_id = f"inv_t{thread_id}_{i}"

                t_request = time.perf_counter_ns()

                # Selection (snapshot read view option)
                target_w = lb.select_target_worker(cap, now_ms, use_snapshot_read_view=use_snapshot)

                # Mutation (takes self._lock inside assign_execution)
                t_acquire_start = time.perf_counter_ns()
                with lb._lock:
                    t_acquired = time.perf_counter_ns()
                    lb.assign_execution(target_w, inv_id, DEFAULT_INITIAL_EPOCH, now_ms)
                    t_released = time.perf_counter_ns()

                t_done = time.perf_counter_ns()

                total_us = (t_done - t_request) / 1000.0
                wait_us = (t_acquired - t_acquire_start) / 1000.0
                hold_us = (t_released - t_acquired) / 1000.0
                contended = wait_us > 1.0

                local_samples.append((total_us, wait_us, hold_us, contended))
            return local_samples

        start_wall = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_task, tid) for tid in range(num_threads)]
            for future in concurrent.futures.as_completed(futures):
                samples = future.result()
                for total_u, wait_u, hold_u, cont in samples:
                    thread_latencies_us.append(total_u)
                    t_waits_us.append(wait_u)
                    t_holds_us.append(hold_u)
                    if cont:
                        contended_count += 1

        end_wall = time.perf_counter()
        wall_ms = (end_wall - start_wall) * 1000.0
        total_ops = num_threads * ops_per_thread
        throughput = (total_ops / wall_ms) * 1000.0 if wall_ms > 0 else 0.0

        thread_latencies_us.sort()
        t_waits_us.sort()
        t_holds_us.sort()

        _, peak_mem_bytes = tracemalloc.get_traced_memory()
        peak_mem_kb = peak_mem_bytes / 1024.0

        def q(sorted_list: List[float], quantile: float) -> float:
            idx = int(len(sorted_list) * quantile)
            return sorted_list[min(idx, len(sorted_list) - 1)]

        p_wait_pct = (contended_count / total_ops) * 100.0 if total_ops > 0 else 0.0

        # Assert Invariant I_9 after execution
        lb.assert_capability_index_consistency()

        mode_label = "SnapshotReadView (V=f(S_A))" if use_snapshot else "GlobalRLock"

        return LockAttributionMetrics(
            mode=mode_label,
            scale_n=scale_n,
            w_c_subset_size=w_c_subset_size,
            thread_count=num_threads,
            ops_total=total_ops,
            throughput_ops_per_sec=round(throughput, 2),
            total_wall_time_ms=round(wall_ms, 2),
            p50_latency_us=round(q(thread_latencies_us, 0.50), 2),
            p95_latency_us=round(q(thread_latencies_us, 0.95), 2),
            p99_latency_us=round(q(thread_latencies_us, 0.99), 2),
            p999_latency_us=round(q(thread_latencies_us, 0.999), 2),
            t_wait_p50_us=round(q(t_waits_us, 0.50), 2),
            t_wait_p99_us=round(q(t_waits_us, 0.99), 2),
            t_hold_p50_us=round(q(t_holds_us, 0.50), 2),
            t_hold_p99_us=round(q(t_holds_us, 0.99), 2),
            p_wait_contention_pct=round(p_wait_pct, 2),
            peak_memory_kb=round(peak_mem_kb, 2),
        )

    def test_benchmark_concurrency_comparison_and_lock_attribution(self) -> None:
        """Runs comparative lock attribution benchmarking between Global RLock and Snapshot Read View."""
        sys_meta = self._get_system_metadata()
        print("\n" + "=" * 105)
        print(" CORTEX SCHEDULER BENCHMARK SUITE — WORKLOAD STANDARDIZATION & LOCK ATTRIBUTION (#50.d.4 / #50.d.6) ")
        print("=" * 105)
        print(f" OS: {sys_meta.system_os} | Arch: {sys_meta.architecture} | CPUs: {sys_meta.logical_cpus}")
        print(f" Python: {sys_meta.python_version} | Clock: {sys_meta.clock_source} | GC: {sys_meta.gc_enabled}")
        print("=" * 105)

        results: List[LockAttributionMetrics] = []

        full_benchmark = os.getenv("CORTEX_BENCHMARK", "0").lower() in ("1", "true", "yes")
        if full_benchmark:
            threads_to_test = [1, 2, 4, 8, 16, 32, 64]
            scales_to_test = [1000, 10000]
        else:
            threads_to_test = [1, 2, 4]
            scales_to_test = [10, 100]

        for scale_n in scales_to_test:
            print(f"\n--- SCALE N = {scale_n} (|W_c| = {max(1, scale_n // 5)}) ---")
            for use_snap in [False, True]:
                mode_str = "Snapshot Read View V=f(S_A)" if use_snap else "Global RLock Baseline"
                print(f"\n[ MODE: {mode_str} ]")
                for c in threads_to_test:
                    # Adjust ops per thread to keep benchmark run duration manageable
                    if full_benchmark:
                        ops_cnt = 50 if scale_n == 1000 else 20
                    else:
                        ops_cnt = 10
                    m = self._profile_lock_attribution(
                        scale_n=scale_n,
                        num_threads=c,
                        use_snapshot=use_snap,
                        ops_per_thread=ops_cnt,
                    )
                    results.append(m)
                    print(
                        f"Threads C={m.thread_count:2d} | "
                        f"Throughput: {m.throughput_ops_per_sec:9.2f} ops/sec | "
                        f"P50: {m.p50_latency_us:7.2f} us | "
                        f"P99: {m.p99_latency_us:8.2f} us | "
                        f"T_wait(P50): {m.t_wait_p50_us:7.2f} us | "
                        f"T_hold(P50): {m.t_hold_p50_us:6.2f} us | "
                        f"P(Wait): {m.p_wait_contention_pct:5.1f}%"
                    )

        print("=" * 105 + "\n")

        # Save artifacts
        out_dir = os.getenv(
            "CORTEX_ARTIFACT_DIR",
            os.path.expanduser("~/.gemini/antigravity/brain/45356e66-d161-49a3-833f-7ca68f18fa84")
        )
        try:
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, "benchmark_lock_attribution_results.json"), "w") as f:
                json.dump(
                    {
                        "system_metadata": asdict(sys_meta),
                        "benchmark_results": [asdict(m) for m in results],
                    },
                    f,
                    indent=2,
                )
        except Exception:
            pass

        self.assertGreater(len(results), 0)


if __name__ == "__main__":
    unittest.main()
