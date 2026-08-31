#!/usr/bin/env python3
"""
Verification Pipeline Resource Profiler & Resource Controller (Issue #51)

Measures peak RSS, CPU time, wall time, process count, and exit status
for each stage of the Cortex verification suite.
"""

from __future__ import annotations

import argparse
import resource
import subprocess
import time
from dataclasses import dataclass
from typing import List


@dataclass
class StageResourceMetrics:
    stage_name: str
    command: str
    exit_code: int
    wall_time_sec: float
    cpu_time_sec: float
    peak_rss_mb: float
    status: str


def get_peak_rss_mb() -> float:
    """Returns maximum resident set size in MB for current process and children."""
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    # ru_maxrss is in kilobytes on Linux
    return round(ru.ru_maxrss / 1024.0, 2)


def run_profiled_stage(stage_name: str, command: str, timeout_sec: int = 300) -> StageResourceMetrics:
    print(f"\n[PROFILER] Starting Stage: {stage_name}")
    print(f"[PROFILER] Command: {command}")

    start_wall = time.perf_counter()
    start_cpu = time.process_time()

    status = "SUCCESS"
    exit_code = 0

    try:
        res = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        exit_code = res.returncode
        if exit_code != 0:
            status = f"FAILED (Exit Code {exit_code})"
    except subprocess.TimeoutExpired:
        status = f"TIMEOUT (Exceeded {timeout_sec}s)"
        exit_code = 124
    except Exception as e:
        status = f"ERROR ({str(e)})"
        exit_code = 1

    end_wall = time.perf_counter()
    end_cpu = time.process_time()

    wall_sec = round(end_wall - start_wall, 2)
    cpu_sec = round(end_cpu - start_cpu, 2)
    peak_rss = get_peak_rss_mb()

    print(f"[PROFILER] Completed {stage_name}: Status={status}, Peak RSS={peak_rss} MB, Wall={wall_sec}s, CPU={cpu_sec}s")

    return StageResourceMetrics(
        stage_name=stage_name,
        command=command,
        exit_code=exit_code,
        wall_time_sec=wall_sec,
        cpu_time_sec=cpu_sec,
        peak_rss_mb=peak_rss,
        status=status,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Cortex Verification Resource Profiler")
    parser.add_argument("--stage", type=str, default="all", help="Stage to run or 'all'")
    args = parser.parse_args()

    stages = [
        ("Coq Kernel Core", "make -C verification Phase5Simulation.vo Phase6WALSafety.vo"),
        ("Coq Full Suite", "make -C verification all-coq"),
        ("Axiom Audit", "make -C verification audit"),
        ("TLA+ Bounded TLC", "java -Xmx1G -XX:+UseParallelGC -cp verification/tla/tla2tools.jar tlc2.TLC -workers 2 verification/tla/Phase6DistributedAuthority.tla -config verification/tla/Phase6DistributedAuthority.cfg"),
        ("Python Conformance", "python3 -m unittest discover -s tests/conformance"),
        ("Python Performance Benchmark", "python3 -m unittest tests/performance/test_scheduler_benchmark.py"),
    ]

    metrics_list: List[StageResourceMetrics] = []

    for name, cmd in stages:
        if args.stage != "all" and args.stage.lower() not in name.lower():
            continue
        m = run_profiled_stage(name, cmd)
        metrics_list.append(m)

    print("\n" + "=" * 85)
    print(" CORTEX VERIFICATION RESOURCE PROFILING SUMMARY ")
    print("=" * 85)
    print(f"{'Stage Name':<30} | {'Status':<15} | {'Peak RSS (MB)':<13} | {'Wall (s)':<8} | {'CPU (s)':<8}")
    print("-" * 85)
    for m in metrics_list:
        print(f"{m.stage_name:<30} | {m.status:<15} | {m.peak_rss_mb:<13.2f} | {m.wall_time_sec:<8.2f} | {m.cpu_time_sec:<8.2f}")
    print("=" * 85 + "\n")


if __name__ == "__main__":
    main()
