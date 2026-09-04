"""
Cortex Effect Pipeline Reproducible Benchmark

Separates and measures each cost component of the LocalProcessMCPAdapter
execution path to establish the empirical performance baseline.

Measurements:
    T_spawn:         Process creation (subprocess.Popen)
    T_serialization: JSON-RPC request encoding
    T_IPC:           communicate() round-trip
    T_cleanup:       Process reap and pipe close
    T_total:         Full execute_effect() call

Workload matrix:
    - 1, 10, 50, 100 sequential effects
    - Tiny (32B), medium (4KB), large (64KB) payloads
    - Success, failure, timeout cases
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import tempfile
import time

# ---------------------------------------------------------------------------
# Benchmark infrastructure
# ---------------------------------------------------------------------------

ITERATIONS_PER_SCENARIO = 20
SCENARIOS = {
    "tiny_payload": 32,
    "medium_payload": 4096,
    "large_payload": 65536,
}

# A minimal echo server script that reads one JSON-RPC request and responds
ECHO_SERVER_SCRIPT = r'''
import json, sys
line = sys.stdin.readline()
req = json.loads(line)
result = {"echoed": True, "size": len(line)}
resp = {"jsonrpc": "2.0", "id": req.get("id", 1), "result": result}
print(json.dumps(resp))
'''

FAIL_SERVER_SCRIPT = r'''
import json, sys
line = sys.stdin.readline()
req = json.loads(line)
resp = {"jsonrpc": "2.0", "id": req.get("id", 1), "error": {"code": -1, "message": "intentional failure"}}
print(json.dumps(resp))
'''

CRASH_SERVER_SCRIPT = r'''
import sys
sys.exit(1)
'''

SLOW_SERVER_SCRIPT = r'''
import json, sys, time
line = sys.stdin.readline()
time.sleep(2.0)
req = json.loads(line)
resp = {"jsonrpc": "2.0", "id": req.get("id", 1), "result": {"delayed": True}}
print(json.dumps(resp))
'''


def write_temp_script(script_content: str) -> str:
    """Write a temporary Python script and return its path."""
    fd, path = tempfile.mkstemp(suffix=".py", prefix="cortex_bench_")
    with os.fdopen(fd, "w") as f:
        f.write(script_content)
    return path


def build_rpc_request(payload_size: int, request_id: str = "bench_001") -> str:
    """Build a JSON-RPC 2.0 request with a payload of approximately payload_size bytes."""
    payload_data = "x" * max(0, payload_size - 100)
    rpc = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {
            "name": "echo",
            "arguments": {"data": payload_data},
        },
    }
    return json.dumps(rpc) + "\n"


# ---------------------------------------------------------------------------
# Component-level measurements
# ---------------------------------------------------------------------------

def measure_spawn_only(server_cmd: list[str], iterations: int) -> list[float]:
    """Measure only subprocess.Popen creation time (no I/O)."""
    times = []
    for _ in range(iterations):
        t0 = time.monotonic()
        proc = subprocess.Popen(
            server_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        t1 = time.monotonic()
        proc.kill()
        proc.communicate()
        times.append((t1 - t0) * 1000)
    return times


def measure_serialization(payload_size: int, iterations: int) -> list[float]:
    """Measure JSON serialization time."""
    times = []
    for _ in range(iterations):
        t0 = time.monotonic()
        _ = build_rpc_request(payload_size)
        t1 = time.monotonic()
        times.append((t1 - t0) * 1000)
    return times


def measure_full_roundtrip(server_cmd: list[str], payload_size: int, iterations: int, timeout: float = 5.0) -> dict:
    """Measure full spawn -> serialize -> communicate -> cleanup cycle."""
    t_spawn_list = []
    t_serial_list = []
    t_ipc_list = []
    t_cleanup_list = []
    t_total_list = []
    success_count = 0
    failure_count = 0

    for i in range(iterations):
        t_total_start = time.monotonic()

        # Serialization
        t_s0 = time.monotonic()
        request_str = build_rpc_request(payload_size, request_id=f"bench_{i:04d}")
        t_s1 = time.monotonic()
        t_serial_list.append((t_s1 - t_s0) * 1000)

        # Spawn
        t_sp0 = time.monotonic()
        try:
            proc = subprocess.Popen(
                server_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError:
            failure_count += 1
            continue
        t_sp1 = time.monotonic()
        t_spawn_list.append((t_sp1 - t_sp0) * 1000)

        # IPC (communicate)
        t_ipc0 = time.monotonic()
        try:
            stdout_data, _ = proc.communicate(input=request_str, timeout=timeout)
            t_ipc1 = time.monotonic()
            t_ipc_list.append((t_ipc1 - t_ipc0) * 1000)

            if proc.returncode == 0 and stdout_data.strip():
                try:
                    resp = json.loads(stdout_data.strip())
                    if "result" in resp:
                        success_count += 1
                    else:
                        failure_count += 1
                except json.JSONDecodeError:
                    failure_count += 1
            else:
                failure_count += 1

        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            failure_count += 1
            t_ipc1 = time.monotonic()
            t_ipc_list.append((t_ipc1 - t_ipc0) * 1000)

        # Cleanup
        t_cl0 = time.monotonic()
        try:
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()
        except Exception:
            pass
        t_cl1 = time.monotonic()
        t_cleanup_list.append((t_cl1 - t_cl0) * 1000)

        t_total_end = time.monotonic()
        t_total_list.append((t_total_end - t_total_start) * 1000)

    return {
        "t_spawn": t_spawn_list,
        "t_serialization": t_serial_list,
        "t_ipc": t_ipc_list,
        "t_cleanup": t_cleanup_list,
        "t_total": t_total_list,
        "success_count": success_count,
        "failure_count": failure_count,
    }


def summarize(label: str, times_ms: list[float]) -> dict:
    """Compute P50, P95, P99, mean, stdev for a list of times."""
    if not times_ms:
        return {"label": label, "count": 0}
    sorted_t = sorted(times_ms)
    n = len(sorted_t)
    return {
        "label": label,
        "count": n,
        "mean_ms": round(statistics.mean(sorted_t), 3),
        "min_ms": round(sorted_t[0], 3),
        "max_ms": round(sorted_t[-1], 3),
        "p50_ms": round(sorted_t[n // 2], 3),
        "p95_ms": round(sorted_t[int(n * 0.95)], 3),
        "p99_ms": round(sorted_t[min(int(n * 0.99), n - 1)], 3),
        "stdev_ms": round(statistics.stdev(sorted_t), 3) if n > 1 else 0.0,
    }


# ---------------------------------------------------------------------------
# Main benchmark harness
# ---------------------------------------------------------------------------

def run_benchmarks():
    print("=" * 80)
    print("CORTEX EFFECT PIPELINE REPRODUCIBLE BENCHMARK")
    print("=" * 80)
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"Iterations per scenario: {ITERATIONS_PER_SCENARIO}")
    print()

    echo_script = write_temp_script(ECHO_SERVER_SCRIPT)
    fail_script = write_temp_script(FAIL_SERVER_SCRIPT)
    crash_script = write_temp_script(CRASH_SERVER_SCRIPT)
    slow_script = write_temp_script(SLOW_SERVER_SCRIPT)

    python_cmd = sys.executable
    echo_cmd = [python_cmd, echo_script]
    fail_cmd = [python_cmd, fail_script]
    crash_cmd = [python_cmd, crash_script]
    slow_cmd = [python_cmd, slow_script]

    all_results = {}

    try:
        # Phase 1: Isolated spawn measurement
        print("-" * 60)
        print("PHASE 1: Isolated Process Spawn Measurement")
        print("-" * 60)
        spawn_times = measure_spawn_only(echo_cmd, ITERATIONS_PER_SCENARIO)
        s = summarize("T_spawn (isolated)", spawn_times)
        all_results["spawn_isolated"] = s
        print(f"  {s['label']}: mean={s['mean_ms']:.2f}ms, P50={s['p50_ms']:.2f}ms, P95={s['p95_ms']:.2f}ms, P99={s['p99_ms']:.2f}ms")
        print()

        # Phase 2: Full roundtrip by payload size
        print("-" * 60)
        print("PHASE 2: Full Roundtrip by Payload Size")
        print("-" * 60)
        for scenario_name, payload_size in SCENARIOS.items():
            results = measure_full_roundtrip(echo_cmd, payload_size, ITERATIONS_PER_SCENARIO)

            print(f"\n  Scenario: {scenario_name} ({payload_size} bytes)")
            print(f"  Success: {results['success_count']}, Failure: {results['failure_count']}")

            for component in ["t_spawn", "t_serialization", "t_ipc", "t_cleanup", "t_total"]:
                s = summarize(f"  {component}", results[component])
                all_results[f"{scenario_name}_{component}"] = s
                if s["count"] > 0:
                    print(f"    {component}: mean={s['mean_ms']:.3f}ms, P50={s['p50_ms']:.3f}ms, P95={s['p95_ms']:.3f}ms")

            # Proportion analysis
            if results["t_total"]:
                total_mean = statistics.mean(results["t_total"])
                spawn_mean = statistics.mean(results["t_spawn"]) if results["t_spawn"] else 0
                ipc_mean = statistics.mean(results["t_ipc"]) if results["t_ipc"] else 0
                serial_mean = statistics.mean(results["t_serialization"]) if results["t_serialization"] else 0
                cleanup_mean = statistics.mean(results["t_cleanup"]) if results["t_cleanup"] else 0
                print("    --- Proportion Analysis ---")
                print(f"    T_spawn:   {spawn_mean:.2f}ms ({spawn_mean/total_mean*100:.1f}%)")
                print(f"    T_IPC:     {ipc_mean:.2f}ms ({ipc_mean/total_mean*100:.1f}%)")
                print(f"    T_serial:  {serial_mean:.3f}ms ({serial_mean/total_mean*100:.2f}%)")
                print(f"    T_cleanup: {cleanup_mean:.3f}ms ({cleanup_mean/total_mean*100:.2f}%)")
                print(f"    T_total:   {total_mean:.2f}ms")
                lambda_max = 1000.0 / total_mean if total_mean > 0 else 0
                print(f"    λ_max (sequential): {lambda_max:.2f} effects/sec")

        # Phase 3: Failure modes
        print()
        print("-" * 60)
        print("PHASE 3: Failure Mode Measurement")
        print("-" * 60)

        # Explicit server error
        fail_results = measure_full_roundtrip(fail_cmd, 32, ITERATIONS_PER_SCENARIO)
        s = summarize("fail_server_total", fail_results["t_total"])
        all_results["fail_server_total"] = s
        print(f"\n  Server Error: mean={s['mean_ms']:.2f}ms, successes={fail_results['success_count']}, failures={fail_results['failure_count']}")

        # Crash
        crash_results = measure_full_roundtrip(crash_cmd, 32, ITERATIONS_PER_SCENARIO)
        s = summarize("crash_server_total", crash_results["t_total"])
        all_results["crash_server_total"] = s
        print(f"  Crash Exit:   mean={s['mean_ms']:.2f}ms, successes={crash_results['success_count']}, failures={crash_results['failure_count']}")

        # Timeout (reduced iterations due to 2s sleep)
        slow_results = measure_full_roundtrip(slow_cmd, 32, min(3, ITERATIONS_PER_SCENARIO), timeout=0.5)
        s = summarize("timeout_server_total", slow_results["t_total"])
        all_results["timeout_server_total"] = s
        print(f"  Timeout:      mean={s['mean_ms']:.2f}ms, successes={slow_results['success_count']}, failures={slow_results['failure_count']}")

        # Phase 4: Sequential burst
        print()
        print("-" * 60)
        print("PHASE 4: Sequential Burst (50 consecutive effects)")
        print("-" * 60)
        burst_results = measure_full_roundtrip(echo_cmd, 256, 50)
        s = summarize("burst_50_total", burst_results["t_total"])
        all_results["burst_50_total"] = s
        if burst_results["t_total"]:
            wall_clock = sum(burst_results["t_total"])
            effective_lambda = 50 / (wall_clock / 1000) if wall_clock > 0 else 0
            print(f"  50 sequential: wall={wall_clock:.0f}ms, mean={s['mean_ms']:.2f}ms, P95={s['p95_ms']:.2f}ms")
            print(f"  Effective λ: {effective_lambda:.2f} effects/sec")
            print(f"  Success: {burst_results['success_count']}, Failure: {burst_results['failure_count']}")

        # Summary
        print()
        print("=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        # Save results
        results_path = os.path.join(os.path.dirname(__file__), "bench_results.json")
        with open(results_path, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"Results saved to: {results_path}")

    finally:
        for p in [echo_script, fail_script, crash_script, slow_script]:
            try:
                os.unlink(p)
            except OSError:
                pass


if __name__ == "__main__":
    run_benchmarks()
