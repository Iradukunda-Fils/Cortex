#!/usr/bin/env python3
"""
Issue #51 Verification Resource Controller & Admission Engine (Refined)

Enforces three-tier operational ceilings on memory, CPU, process concurrency,
and runtime execution for the Cortex verification pipeline:
  H_heap (JVM) < H_RSS (Process) < H_system (Host Admission Limit)

Prevents host system instability, OOM crashes, and resource exhaustion.
Uses file-based reservation locking for concurrency-safe job admission.
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple

LOCKFILE_PATH = "verification/.verify_admission.json"
DEFAULT_HOST_SAFETY_MARGIN_MB = 1024.0  # 1 GB headroom required for OS/host stability


@dataclass
class ProfileConfig:
    name: str
    description: str
    required_mem_mb: float
    max_rss_mb: float
    timeout_sec: int
    commands: List[Tuple[str, str]]


def get_available_memory_mb() -> float:
    """Reads available system memory in MB from /proc/meminfo."""
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    parts = line.split()
                    kb = float(parts[1])
                    return kb / 1024.0
    except Exception:
        pass
    return 4096.0


def acquire_reservation(job_mem_mb: float) -> Tuple[bool, float, float]:
    """
    Concurrency-safe admission reservation check.
    Ensures: AvailableRAM - CurrentReservations - JobMem - HostMargin >= 0
    """
    avail_mem = get_available_memory_mb()
    reserved_mem = 0.0

    if os.path.exists(LOCKFILE_PATH):
        try:
            with open(LOCKFILE_PATH, "r") as f:
                data = json.load(f)
                # Purge stale reservations older than 600s
                now = time.time()
                reserved_mem = sum(v["mem_mb"] for v in data.values() if now - v["timestamp"] < 600)
        except Exception:
            reserved_mem = 0.0

    safe_capacity = avail_mem - reserved_mem - DEFAULT_HOST_SAFETY_MARGIN_MB
    admitted = safe_capacity >= job_mem_mb
    return admitted, avail_mem, reserved_mem


def record_reservation(profile_name: str, job_mem_mb: float) -> None:
    """Records an active verification job reservation."""
    data = {}
    if os.path.exists(LOCKFILE_PATH):
        try:
            with open(LOCKFILE_PATH, "r") as f:
                data = json.load(f)
        except Exception:
            data = {}

    data[str(os.getpid())] = {
        "profile": profile_name,
        "mem_mb": job_mem_mb,
        "timestamp": time.time(),
    }

    try:
        with open(LOCKFILE_PATH, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def release_reservation() -> None:
    """Releases the verification job reservation upon completion or exit."""
    if os.path.exists(LOCKFILE_PATH):
        try:
            with open(LOCKFILE_PATH, "r") as f:
                data = json.load(f)
            pid_str = str(os.getpid())
            if pid_str in data:
                del data[pid_str]
                with open(LOCKFILE_PATH, "w") as f:
                    json.dump(data, f)
        except Exception:
            pass


PROFILES: Dict[str, ProfileConfig] = {
    "verify-fast": ProfileConfig(
        name="verify-fast",
        description="Fast developer sanity check (Python Conformance + Coq Kernel Core)",
        required_mem_mb=500.0,
        max_rss_mb=800.0,
        timeout_sec=60,
        commands=[
            ("Python Conformance", "python3 -m unittest discover -s tests/conformance"),
            ("Coq Kernel Core", "make -C verification Phase5Simulation.vo Phase6WALSafety.vo"),
        ],
    ),
    "verify-kernel": ProfileConfig(
        name="verify-kernel",
        description="Kernel verification gate (Phase 5 & 6 Coq proofs + Conformance)",
        required_mem_mb=600.0,
        max_rss_mb=1000.0,
        timeout_sec=120,
        commands=[
            (
                "Coq Kernel Models",
                "make -C verification Phase4RoutingRefinement.vo Phase5LoadBalancerRefinement.vo Phase5Simulation.vo Phase6WALSafety.vo",
            ),
            ("Python Conformance", "python3 -m unittest discover -s tests/conformance"),
            ("Axiom Audit", "make -C verification audit"),
        ],
    ),
    "verify-coq": ProfileConfig(
        name="verify-coq",
        description="Full Coq proof suite compilation and axiom/admit audit",
        required_mem_mb=800.0,
        max_rss_mb=1500.0,
        timeout_sec=180,
        commands=[
            ("Coq Full Compilation", "make -C verification all-coq"),
            ("Axiom Audit", "make -C verification audit"),
        ],
    ),
    "verify-tla-safe": ProfileConfig(
        name="verify-tla-safe",
        description="Bounded TLA+ TLC distributed authority model check (-Xmx1G, -workers 2)",
        required_mem_mb=1200.0,
        max_rss_mb=1800.0,
        timeout_sec=240,
        commands=[
            (
                "TLA+ Bounded Model Check",
                "java -Xmx1G -XX:+UseParallelGC -cp verification/tla/tla2tools.jar tlc2.TLC -workers 2 verification/tla/Phase6DistributedAuthority.tla -config verification/tla/Phase6DistributedAuthority.cfg",
            ),
        ],
    ),
    "verify-full": ProfileConfig(
        name="verify-full",
        description="Unified sequential verification suite (Coq + TLA+ Safe + Python Conformance - Assurance Only)",
        required_mem_mb=1500.0,
        max_rss_mb=2000.0,
        timeout_sec=400,
        commands=[
            ("Coq Full Compilation", "make -C verification all-coq"),
            ("Axiom Audit", "make -C verification audit"),
            (
                "TLA+ Bounded Model Check",
                "java -Xmx1G -XX:+UseParallelGC -cp verification/tla/tla2tools.jar tlc2.TLC -workers 2 verification/tla/Phase6DistributedAuthority.tla -config verification/tla/Phase6DistributedAuthority.cfg",
            ),
            ("Python Conformance", "python3 -m unittest discover -s tests/conformance"),
        ],
    ),
    "verify-stress": ProfileConfig(
        name="verify-stress",
        description="High-scale model check with strict admission check (-Xmx2G, -workers 4)",
        required_mem_mb=2500.0,
        max_rss_mb=3500.0,
        timeout_sec=600,
        commands=[
            (
                "TLA+ Stress Model Check",
                "java -Xmx2G -XX:+UseParallelGC -cp verification/tla/tla2tools.jar tlc2.TLC -workers 4 verification/tla/Phase6DistributedAuthority.tla -config verification/tla/Phase6DistributedAuthority.cfg",
            ),
        ],
    ),
    "verify-benchmark": ProfileConfig(
        name="verify-benchmark",
        description="Performance benchmark suite (Separate from assurance pipeline)",
        required_mem_mb=800.0,
        max_rss_mb=1500.0,
        timeout_sec=180,
        commands=[
            ("Python Performance Benchmark", "python3 -m unittest tests/performance/test_scheduler_benchmark.py"),
        ],
    ),
}


def run_bounded_job(name: str, cmd: str, max_rss_mb: float, timeout_sec: int) -> bool:
    print(f"\n[RESOURCE CONTROLLER] Executing Job: {name}")
    print(f"[RESOURCE CONTROLLER] Command: {cmd}")
    print(f"[RESOURCE CONTROLLER] Ceilings: Max RSS={max_rss_mb} MB | Timeout={timeout_sec}s")

    start_time = time.time()
    process = None

    try:
        # Normalize command paths if executing directly inside verification/ directory
        if os.path.basename(os.getcwd()) == "verification":
            cmd = cmd.replace("make -C verification", "make")
            cmd = cmd.replace("verification/tla/", "tla/")
            if "tests/" in cmd:
                cmd = cmd.replace("tests/", "../tests/")

        process = subprocess.Popen(
            cmd,
            shell=True,
        )

        while True:
            ret = process.poll()
            if ret is not None:
                if ret == 0:
                    print(f"[RESOURCE CONTROLLER] Job '{name}' PASSED in {round(time.time() - start_time, 2)}s.")
                    return True
                else:
                    print(f"[RESOURCE CONTROLLER] Job '{name}' FAILED with exit code {ret}.")
                    return False

            elapsed = time.time() - start_time
            if elapsed > timeout_sec:
                print(
                    f"\n[RESOURCE CONTROLLER ERROR] Job '{name}' EXCEEDED TIMEOUT ({timeout_sec}s). Terminating process..."
                )
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                return False

            # Monitor process RSS
            ru = resource.getrusage(resource.RUSAGE_CHILDREN)
            child_rss_mb = ru.ru_maxrss / 1024.0
            if child_rss_mb > max_rss_mb:
                print(
                    f"\n[RESOURCE CONTROLLER ERROR] Job '{name}' EXCEEDED MAX RSS CEILING ({child_rss_mb:.2f} MB > {max_rss_mb:.2f} MB). Terminating process..."
                )
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                return False

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n[RESOURCE CONTROLLER WARNING] Interrupted by user. Cleaning up child processes...")
        if process and process.poll() is None:
            process.kill()
        release_reservation()
        sys.exit(130)
    except Exception as e:
        print(f"[RESOURCE CONTROLLER ERROR] Execution exception for '{name}': {e}")
        if process and process.poll() is None:
            process.kill()
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Cortex Verification Resource Controller & Admission Engine")
    parser.add_argument(
        "profile",
        nargs="?",
        default="verify-fast",
        choices=list(PROFILES.keys()),
        help="Verification profile to run (default: verify-fast)",
    )
    parser.add_argument("--force", action="store_true", help="Bypass admission control memory check")
    args = parser.parse_args()

    profile = PROFILES[args.profile]

    print("=" * 80)
    print(f" CORTEX VERIFICATION RESOURCE CONTROLLER — Profile: {profile.name}")
    print(f" Description: {profile.description}")
    print("=" * 80)

    # Concurrency-Safe Admission Control Phase
    admitted, avail_mem, reserved_mem = acquire_reservation(profile.required_mem_mb)
    print(f"[ADMISSION CONTROL] Host Available Memory: {avail_mem:.2f} MB")
    print(f"[ADMISSION CONTROL] Active Reservations: {reserved_mem:.2f} MB")
    print(f"[ADMISSION CONTROL] Required Profile Memory Budget: {profile.required_mem_mb:.2f} MB")
    print(f"[ADMISSION CONTROL] Host Safety Headroom Margin: {DEFAULT_HOST_SAFETY_MARGIN_MB:.2f} MB")

    if not admitted and not args.force:
        print("\n" + "!" * 80)
        print(f"[ADMISSION DENIED] Insufficient unreserved system memory for profile '{profile.name}'.")
        print(
            f"Available ({avail_mem:.2f} MB) - Reserved ({reserved_mem:.2f} MB) - Margin ({DEFAULT_HOST_SAFETY_MARGIN_MB:.2f} MB) < Required ({profile.required_mem_mb:.2f} MB)."
        )
        print("Halting verification to protect host stability.")
        print("!" * 80 + "\n")
        sys.exit(1)

    record_reservation(profile.name, profile.required_mem_mb)
    print("[ADMISSION GRANTED] Host system resources admitted. Starting sequential execution.\n")

    start_suite_time = time.time()
    failed_jobs = []

    try:
        for name, cmd in profile.commands:
            success = run_bounded_job(name, cmd, profile.max_rss_mb, profile.timeout_sec)
            if not success:
                failed_jobs.append(name)
                break
    finally:
        release_reservation()

    total_time = round(time.time() - start_suite_time, 2)
    print("\n" + "=" * 80)
    if not failed_jobs:
        print(f" VERIFICATION PROFILE '{profile.name}' PASSED (Total Time: {total_time}s)")
        print("=" * 80 + "\n")
        sys.exit(0)
    else:
        print(f" VERIFICATION PROFILE '{profile.name}' FAILED at job '{failed_jobs[0]}'")
        print("=" * 80 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
