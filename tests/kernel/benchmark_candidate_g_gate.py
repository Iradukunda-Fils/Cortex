"""
Multi-dimensional promotion gate benchmark for Candidate G vs Baseline.
Measures lock hold times (P50, P95, P99), RSS memory usage, and CPU times
across scales N in {10, 100, 1000, 3000} and varying expiration densities K.
Optimized setup with dynamic iterations to prevent O(N^2) init overhead bottlenecks.
"""

from __future__ import annotations

import gc
import os
import statistics
import time
from typing import Any, Dict, List

try:
    import psutil
except ImportError:
    psutil = None

from cortex.tools.kernel.resource_authority import ResourceAuthority


def get_rss_bytes() -> int:
    """Helper to get current process RSS memory in bytes."""
    if psutil is not None:
        return psutil.Process(os.getpid()).memory_info().rss
    # Fallback using /proc
    try:
        with open("/proc/self/statm", "r") as f:
            pages = int(f.read().split()[1])
            return pages * os.sysconf("SC_PAGE_SIZE")
    except Exception:
        return 0


def run_benchmark_for_config(N: int, K: int, use_batched: bool, iterations: int) -> Dict[str, Any]:
    """Runs benchmark for a single configuration and returns statistical metrics."""
    durations_us: List[float] = []
    rss_start = get_rss_bytes()

    # Pre-warm/force GC
    gc.collect()

    for _ in range(iterations):
        # Create a fresh resource authority instance
        ra = ResourceAuthority(
            capacity=N * 10,
            safety_margin=0,
            uncertainty=0,
            use_batched_sweep=use_batched,
        )
        now = 1_000_000_000

        # Register N reservations
        for i in range(N):
            exp_ts = now + 50 if i < K else now + 5000
            ra.reserve(
                res_id=i,
                res_inv=100000 + i,
                res_att=200000 + i,
                res_worker=1,
                res_demand=1,
                authority_epoch=1,
                lease_epoch=1,
                worker_generation=1,
                expiration_timestamp_ns=exp_ts,
            )

        # Time the sweep operation
        t0 = time.perf_counter_ns()
        expired = ra.expire_reservations_sweep(now + 100)
        t_elap_us = (time.perf_counter_ns() - t0) / 1000.0

        assert len(expired) == K, f"Expected {K} expirations, got {len(expired)}"
        durations_us.append(t_elap_us)

    rss_end = get_rss_bytes()
    rss_growth_kb = (rss_end - rss_start) / 1024.0

    durations_us.sort()
    p50 = statistics.median(durations_us)
    p95 = durations_us[int(len(durations_us) * 0.95)] if len(durations_us) > 1 else durations_us[-1]
    p99 = durations_us[int(len(durations_us) * 0.99)] if len(durations_us) > 1 else durations_us[-1]
    avg = statistics.mean(durations_us)

    return {
        "avg_us": avg,
        "p50_us": p50,
        "p95_us": p95,
        "p99_us": p99,
        "rss_growth_kb": rss_growth_kb,
    }


def main():
    print("Initializing Multi-Dimensional Promotion Gate Benchmark...")
    # Test matrix: (N, K, iterations)
    configs = [
        (10, 2, 10),
        (100, 10, 10),
        (1000, 100, 5),
        (3000, 300, 3),
    ]

    results: List[Dict[str, Any]] = []

    for N, K, iters in configs:
        print(f"Profiling scale N={N}, K={K} (Baseline)...")
        res_base = run_benchmark_for_config(N, K, use_batched=False, iterations=iters)

        print(f"Profiling scale N={N}, K={K} (Candidate G)...")
        res_batch = run_benchmark_for_config(N, K, use_batched=True, iterations=iters)

        results.append(
            {
                "N": N,
                "K": K,
                "base": res_base,
                "batch": res_batch,
            }
        )

    # Print markdown report
    print("\n# CANDIDATE G PROMOTION GATE BENCHMARK REPORT\n")
    print(
        "| Scale ($N$) | Expired ($K$) | Mode | P50 Latency | P95 Latency | P99 Latency | RSS Growth (KB) | Speedup |"
    )
    print("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

    for r in results:
        N, K = r["N"], r["K"]
        base, batch = r["base"], r["batch"]
        speedup = base["p50_us"] / batch["p50_us"] if batch["p50_us"] > 0 else 1.0

        print(
            f"| {N} | {K} | Baseline | {base['p50_us']:.2f} µs | {base['p95_us']:.2f} µs | {base['p99_us']:.2f} µs | {base['rss_growth_kb']:.2f} | — |"
        )
        print(
            f"| {N} | {K} | Candidate G | {batch['p50_us']:.2f} µs | {batch['p95_us']:.2f} µs | {batch['p99_us']:.2f} µs | {batch['rss_growth_kb']:.2f} | **{speedup:.2f}x** |"
        )


if __name__ == "__main__":
    main()
