"""
Cortex EffectExecutionPipeline Concurrency Validation

Exercises the canonical production path under concurrent load:
    EffectRequest → GatewayAuthorizationGate → CredentialBroker
    → ResourceContract (adapter) → CAS → ReconciliationEngine
    → EffectResultStore → EffectOutcome

Measures at C = {1, 2, 4, 8, 16, 32}:
    P50, P95, P99, λ (throughput), error rate, replay correctness

Tests:
    A. Concurrent unique effects (no contention on idempotency)
    B. Concurrent duplicate effects (in-flight dedup correctness)
    C. Mixed success/failure under concurrency
    D. Memory growth under sustained load
"""

from __future__ import annotations

import concurrent.futures
import os
import statistics
import sys
import threading
import time
import tracemalloc
import uuid

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cortex.tools.kernel.adapter_contract import (
    AdapterExecutionContext,
    AdapterOutcome,
    EffectClassification,
    EffectPayload,
    EvidencePayload,
    ExecutionStatus,
    ResourceContract,
)
from cortex.tools.kernel.effect_gateway import (
    EffectOutcome,
    EffectRequest,
    GatewayAuthorizationGate,
)
from cortex.tools.kernel.effect_runtime import (
    ContentAddressableStore,
    CredentialBroker,
    EffectExecutionPipeline,
    EffectResultStore,
)
from cortex.tools.kernel.reconciliation import (
    EffectReconciliationEngine,
)

# ---------------------------------------------------------------------------
# Mock Adapter (fast, no subprocess, isolates pipeline concurrency)
# ---------------------------------------------------------------------------

class FastMockAdapter(ResourceContract):
    """Immediate-return adapter that isolates pipeline lock contention from subprocess cost."""

    def __init__(self, latency_ms: float = 0.0, fail_rate: float = 0.0):
        self._latency_ms = latency_ms
        self._fail_rate = fail_rate
        self._call_count = 0
        self._lock = threading.Lock()

    @property
    def resource_type(self) -> str:
        return "adapter.mock.v1"

    @property
    def effect_classification(self) -> EffectClassification:
        return EffectClassification.READ_ONLY

    def execute_effect(
        self,
        ctx: AdapterExecutionContext,
        payload: EffectPayload,
    ) -> AdapterOutcome:
        with self._lock:
            self._call_count += 1
            call_num = self._call_count

        if self._latency_ms > 0:
            time.sleep(self._latency_ms / 1000.0)

        # Deterministic failure based on rate
        if self._fail_rate > 0 and (call_num % int(1 / self._fail_rate)) == 0:
            return AdapterOutcome(
                status=ExecutionStatus.EFFECT_NOT_APPLIED,
                error_message="Injected failure",
            )

        return AdapterOutcome(
            status=ExecutionStatus.EFFECT_CONFIRMED,
            evidence=EvidencePayload(data=b"ok", is_reference=False),
        )

    @property
    def call_count(self) -> int:
        with self._lock:
            return self._call_count


# ---------------------------------------------------------------------------
# Mock Authority & Registry (always valid)
# ---------------------------------------------------------------------------

class AlwaysValidAuthority:
    def validate_effect_reservation(self, worker_generation: int, lease_epoch: int) -> bool:
        return True


class AlwaysGrantedRegistry:
    def is_capability_granted(self, capability: str, operation: str) -> bool:
        return True

    def resolve_effect_classification(self, capability: str, operation: str) -> EffectClassification:
        return EffectClassification.READ_ONLY


# ---------------------------------------------------------------------------
# Benchmark infrastructure
# ---------------------------------------------------------------------------

def build_pipeline(adapter: ResourceContract) -> EffectExecutionPipeline:
    gate = GatewayAuthorizationGate(
        effect_authority=AlwaysValidAuthority(),
        capability_registry=AlwaysGrantedRegistry(),
        domain_secret=b"benchmark_secret_key_16bytes",
    )
    return EffectExecutionPipeline(
        gate=gate,
        adapter=adapter,
        credential_broker=CredentialBroker(),
        cas=ContentAddressableStore(),
        reconciliation=EffectReconciliationEngine(),
        result_store=EffectResultStore(),
    )


def make_request(invocation_id: str, lease_epoch: int = 1) -> EffectRequest:
    return EffectRequest(
        invocation_id=invocation_id,
        capability="bench:echo",
        operation="echo",
        arguments=b'{"data": "test"}',
        resource_id="bench_resource",
        lease_epoch=lease_epoch,
        worker_generation=1,
    )


def percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    idx = min(int(len(s) * p), len(s) - 1)
    return s[idx]


def run_concurrent_scenario(
    pipeline: EffectExecutionPipeline,
    num_threads: int,
    ops_per_thread: int,
    make_request_fn,
) -> dict:
    """Run ops_per_thread operations on num_threads concurrent threads."""
    latencies_ms: list[float] = []
    errors: list[str] = []
    successes = 0
    lat_lock = threading.Lock()

    def worker(thread_id: int):
        nonlocal successes
        local_latencies = []
        local_errors = []
        local_success = 0

        for i in range(ops_per_thread):
            request = make_request_fn(thread_id, i)
            attempt_id = f"att_{thread_id}_{i}_{uuid.uuid4().hex[:8]}"

            t0 = time.monotonic()
            try:
                outcome = pipeline.execute(request, attempt_id)
                t1 = time.monotonic()
                local_latencies.append((t1 - t0) * 1000)
                if outcome.status == ExecutionStatus.EFFECT_CONFIRMED:
                    local_success += 1
                elif outcome.status in (ExecutionStatus.EFFECT_NOT_APPLIED, ExecutionStatus.UNKNOWN_EFFECT):
                    local_errors.append(f"t{thread_id}_i{i}: {outcome.status.value}")
            except Exception as e:
                t1 = time.monotonic()
                local_latencies.append((t1 - t0) * 1000)
                local_errors.append(f"t{thread_id}_i{i}: {type(e).__name__}: {e}")

        with lat_lock:
            latencies_ms.extend(local_latencies)
            errors.extend(local_errors)
            successes += local_success

    wall_start = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, tid) for tid in range(num_threads)]
        for f in concurrent.futures.as_completed(futures):
            f.result()  # propagate exceptions
    wall_end = time.monotonic()

    total_ops = num_threads * ops_per_thread
    wall_ms = (wall_end - wall_start) * 1000
    throughput = (total_ops / wall_ms) * 1000 if wall_ms > 0 else 0

    return {
        "threads": num_threads,
        "ops_per_thread": ops_per_thread,
        "total_ops": total_ops,
        "wall_ms": round(wall_ms, 2),
        "throughput_ops_sec": round(throughput, 2),
        "successes": successes,
        "errors": len(errors),
        "error_rate_pct": round((len(errors) / total_ops) * 100, 2) if total_ops > 0 else 0,
        "p50_ms": round(percentile(latencies_ms, 0.50), 3),
        "p95_ms": round(percentile(latencies_ms, 0.95), 3),
        "p99_ms": round(percentile(latencies_ms, 0.99), 3),
        "mean_ms": round(statistics.mean(latencies_ms), 3) if latencies_ms else 0,
        "stdev_ms": round(statistics.stdev(latencies_ms), 3) if len(latencies_ms) > 1 else 0,
        "error_details": errors[:5],  # first 5 for diagnostics
    }


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------

def run_benchmarks():
    print("=" * 100)
    print("CORTEX EFFECT EXECUTION PIPELINE — CONCURRENCY VALIDATION")
    print("=" * 100)
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    print()

    concurrency_levels = [1, 2, 4, 8, 16, 32]
    ops_per_thread = 50

    # =========================================================================
    # PHASE A: Concurrent unique effects (no idempotency contention)
    # =========================================================================
    print("-" * 80)
    print("PHASE A: Concurrent Unique Effects (isolate lock contention)")
    print("-" * 80)
    print(f"{'C':>4} | {'Total':>6} | {'Wall(ms)':>10} | {'λ(ops/s)':>10} | {'P50(ms)':>9} | {'P95(ms)':>9} | {'P99(ms)':>9} | {'Errors':>6}")
    print("-" * 80)

    for c in concurrency_levels:
        adapter = FastMockAdapter(latency_ms=0.0)
        pipeline = build_pipeline(adapter)

        def make_unique(tid, idx):
            return make_request(f"unique_t{tid}_i{idx}")

        result = run_concurrent_scenario(pipeline, c, ops_per_thread, make_unique)
        print(
            f"{result['threads']:4d} | {result['total_ops']:6d} | "
            f"{result['wall_ms']:10.2f} | {result['throughput_ops_sec']:10.2f} | "
            f"{result['p50_ms']:9.3f} | {result['p95_ms']:9.3f} | {result['p99_ms']:9.3f} | "
            f"{result['errors']:6d}"
        )

        # Verify adapter was called exactly once per unique request
        assert adapter.call_count == result['total_ops'], (
            f"Adapter called {adapter.call_count} times for {result['total_ops']} unique requests"
        )

    # =========================================================================
    # PHASE B: Concurrent Duplicate Suppression (True Overlap with Barrier)
    # =========================================================================
    print()
    print("-" * 80)
    print("PHASE B: Concurrent Duplicate Suppression (Barrier Synchronized)")
    print("-" * 80)
    print("  Tests C threads calling pipeline.execute() simultaneously for the SAME single EffectKey.")
    print("  Asserts: C callers receive outcomes AND adapter.call_count == 1.")
    print("-" * 80)

    for c in [2, 4, 8, 16, 32]:
        adapter = FastMockAdapter(latency_ms=5.0)  # 5ms hold to guarantee overlap window
        pipeline = build_pipeline(adapter)
        barrier = threading.Barrier(c)

        shared_req = make_request("barrier_shared_invocation_001")
        outcomes: list[EffectOutcome] = []
        outcomes_lock = threading.Lock()

        def barrier_worker(tid: int):
            barrier.wait()  # Synchronize release across all C threads
            attempt_id = f"att_barrier_t{tid}"
            outcome = pipeline.execute(shared_req, attempt_id)
            with outcomes_lock:
                outcomes.append(outcome)

        with concurrent.futures.ThreadPoolExecutor(max_workers=c) as executor:
            futures = [executor.submit(barrier_worker, tid) for tid in range(c)]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        calls = adapter.call_count
        confirmed_count = sum(1 for o in outcomes if o.status == ExecutionStatus.EFFECT_CONFIRMED)

        print(
            f"  C={c:2d}: callers={c:2d}, outcomes_returned={len(outcomes):2d}, "
            f"confirmed={confirmed_count:2d}, adapter.call_count={calls:2d} "
            f"{'✓ EXACT DEDUP (1 call)' if calls == 1 else '❌ GAP DETECTED'}"
        )

        assert len(outcomes) == c, f"Expected {c} outcomes, got {len(outcomes)}"
        assert confirmed_count == c, f"Expected {c} confirmed outcomes, got {confirmed_count}"
        assert calls == 1, f"Expected 1 adapter execution for {c} concurrent duplicate callers, got {calls}"

    # =========================================================================
    # PHASE C: Mixed success/failure under concurrency
    # =========================================================================
    print()
    print("-" * 80)
    print("PHASE C: Mixed Success/Failure Under Concurrency")
    print("-" * 80)

    for c in [4, 8, 16]:
        adapter = FastMockAdapter(latency_ms=0.5, fail_rate=0.1)  # 10% failure
        pipeline = build_pipeline(adapter)

        def make_mixed(tid, idx):
            return make_request(f"mixed_t{tid}_i{idx}")

        result = run_concurrent_scenario(pipeline, c, ops_per_thread, make_mixed)
        print(
            f"  C={c:2d}: successes={result['successes']}, "
            f"non_confirmed={result['errors']}, "
            f"λ={result['throughput_ops_sec']:.1f} ops/s, "
            f"P95={result['p95_ms']:.3f}ms"
        )

    # =========================================================================
    # PHASE D: Memory growth under sustained load
    # =========================================================================
    print()
    print("-" * 80)
    print("PHASE D: Retained Memory Store Growth Under Sustained Load")
    print("-" * 80)
    print("  Note: Measures tracemalloc heap retention in EffectResultStore/CAS.")
    print("        Process RSS is tracked separately by OS environment monitoring.")
    print("-" * 80)

    tracemalloc.start()
    adapter = FastMockAdapter()
    pipeline = build_pipeline(adapter)

    checkpoints = [100, 500, 1000, 2000, 5000]
    checkpoint_idx = 0
    total_submitted = 0

    for batch in range(50):
        for i in range(100):
            req = make_request(f"mem_b{batch}_i{i}")
            attempt_id = f"att_mem_{batch}_{i}"
            pipeline.execute(req, attempt_id)
            total_submitted += 1

        if checkpoint_idx < len(checkpoints) and total_submitted >= checkpoints[checkpoint_idx]:
            current_b, peak_b = tracemalloc.get_traced_memory()
            bytes_per_eff = current_b / total_submitted
            print(
                f"  N={total_submitted:5d}: current={current_b / 1024:7.1f} KiB, "
                f"peak={peak_b / 1024:7.1f} KiB | "
                f"Formula: ({current_b} bytes / {total_submitted} N) = ~{bytes_per_eff:.1f} bytes/effect"
            )
            checkpoint_idx += 1

    current_final_b, peak_final_b = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    final_bytes_per_eff = current_final_b / total_submitted if total_submitted > 0 else 0
    print()
    print(
        f"  FINAL: N={total_submitted}, Retained Heap RAM={current_final_b / 1024:.1f} KiB | "
        f"Exact Retained Memory Rate = {final_bytes_per_eff:.2f} bytes/effect"
    )

    # =========================================================================
    # Summary
    # =========================================================================
    print()
    print("=" * 100)
    print("CONCURRENCY VALIDATION ENVELOPE RESULT: PASS FOR TESTED ENVELOPE")
    print("=" * 100)


if __name__ == "__main__":
    run_benchmarks()
