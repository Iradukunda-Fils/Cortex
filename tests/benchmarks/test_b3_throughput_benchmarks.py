"""
Sub-Gate B.3.1 Benchmark Suite — Durability, Latency Distribution, & Concurrency Profiling

Measures empirical performance bounds across 4 core dimensions:
    1. Single-Threaded IOPS & Latency Percentiles (P50, P95, P99).
    2. Concurrency Scaling (C in {1, 2, 4, 8, 16, 32} concurrent writers).
    3. Latency Decomposition (T_serialize vs T_flock vs T_fsync).
    4. Empirical Decision Record Generation.
"""

from __future__ import annotations

import concurrent.futures
import fcntl
import json
import os
import shutil
import struct
import tempfile
import time
import unittest
import zlib
from typing import List, Tuple

from cortex.tools.kernel.effect_wal import EffectWALEngine, EffectWALState


class TestSubGateB31_ThroughputBenchmarks(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _calculate_percentiles(self, latencies_ms: List[float]) -> Tuple[float, float, float]:
        sorted_lat = sorted(latencies_ms)
        n = len(sorted_lat)
        if n == 0:
            return 0.0, 0.0, 0.0
        p50 = sorted_lat[int(n * 0.50)]
        p95 = sorted_lat[int(n * 0.95)]
        p99 = sorted_lat[min(int(n * 0.99), n - 1)]
        return p50, p95, p99

    def test_b31_single_threaded_fsync_distribution(self) -> None:
        """Measures single-threaded write latency distribution (P50, P95, P99) and IOPS."""

        engine = EffectWALEngine(self.temp_dir)
        num_records = 200
        latencies_ms: List[float] = []

        start_total = time.perf_counter()
        for i in range(num_records):
            t0 = time.perf_counter()
            engine.append_record(
                invocation_id=f"inv_{i}",
                effect_key=f"key_{i}",
                lease_epoch=10,
                authority_epoch=1,
                state=EffectWALState.ACTUATING,
                payload=b'{"bench": true}',
            )
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)
        total_time = time.perf_counter() - start_total
        engine.close()

        iops = num_records / total_time
        p50, p95, p99 = self._calculate_percentiles(latencies_ms)

        print("\n" + "=" * 60)
        print(" [B.3.1 Benchmark] 1. Single-Threaded fsync Latency Distribution")
        print("=" * 60)
        print(f" Total Records:     {num_records}")
        print(f" Total Time:        {total_time:.4f} s")
        print(f" Throughput (IOPS): {iops:.2f} ops/sec")
        print(f" P50 Latency:       {p50:.3f} ms")
        print(f" P95 Latency:       {p95:.3f} ms")
        print(f" P99 Latency:       {p99:.3f} ms")
        print("=" * 60)

        self.assertGreater(iops, 0.0)

    def test_b31_concurrency_scaling(self) -> None:
        """Measures contention and throughput scaling across C in {1, 2, 4, 8, 16} concurrent writers."""
        concurrency_levels = [1, 2, 4, 8, 16]
        records_per_thread = 40

        print("\n" + "=" * 60)
        print(" [B.3.1 Benchmark] 2. Concurrency Scaling Matrix")
        print("=" * 60)
        print(" Threads (C) | Total Ops | Throughput (ops/s) | P50 (ms) | P95 (ms) | P99 (ms)")
        print("-" * 66)

        for c in concurrency_levels:
            wal_dir = os.path.join(self.temp_dir, f"conc_{c}")
            engine = EffectWALEngine(wal_dir)

            def worker(thread_idx: int) -> List[float]:
                l_ms: List[float] = []
                for i in range(records_per_thread):
                    t0 = time.perf_counter()
                    engine.append_record(
                        invocation_id=f"inv_t{thread_idx}_{i}",
                        effect_key=f"key_t{thread_idx}_{i}",
                        lease_epoch=10,
                        authority_epoch=1,
                        state=EffectWALState.ACTUATING,
                        payload=b'{"bench": true}',
                    )
                    l_ms.append((time.perf_counter() - t0) * 1000.0)
                return l_ms

            start_t = time.perf_counter()
            all_latencies: List[float] = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=c) as executor:
                futures = [executor.submit(worker, t_id) for t_id in range(c)]
                for f in concurrent.futures.as_completed(futures):
                    all_latencies.extend(f.result())
            elapsed = time.perf_counter() - start_t
            engine.close()

            total_ops = c * records_per_thread
            iops = total_ops / elapsed
            p50, p95, p99 = self._calculate_percentiles(all_latencies)

            print(f" {c:11d} | {total_ops:9d} | {iops:18.2f} | {p50:8.3f} | {p95:8.3f} | {p99:8.3f}")

        print("=" * 60)

    def test_b31_latency_decomposition(self) -> None:
        """Decomposes write latency into T_serialize, T_flock, and T_fsync."""
        wal_file = os.path.join(self.temp_dir, "decomp.wal")

        n_samples = 100
        t_serialize_list: List[float] = []
        t_flock_list: List[float] = []
        t_fsync_list: List[float] = []

        with open(wal_file, "a+b") as f:
            fd = f.fileno()
            for i in range(n_samples):
                # 1. Measure Serialization
                t0 = time.perf_counter()
                payload_dict = {
                    "seq_no": i + 1,
                    "invocation_id": f"inv_{i}",
                    "effect_key": f"key_{i}",
                    "lease_epoch": 10,
                    "authority_epoch": 1,
                    "state": EffectWALState.ACTUATING.value,
                    "payload_hex": b'{"bench": true}'.hex(),
                    "outcome": None,
                    "error_message": None,
                }
                p_bytes = json.dumps(payload_dict, sort_keys=True).encode("utf-8")
                crc = zlib.crc32(p_bytes) & 0xFFFFFFFF
                header = struct.pack(">4sIIQ", b"CWAL", len(p_bytes), crc, i + 1)
                serialized = header + p_bytes
                t_serialize_list.append((time.perf_counter() - t0) * 1000.0)

                # 2. Measure fcntl.flock Lock Overhead
                t0 = time.perf_counter()
                fcntl.flock(fd, fcntl.LOCK_EX)
                t_flock_list.append((time.perf_counter() - t0) * 1000.0)

                try:
                    f.seek(0, os.SEEK_END)
                    f.write(serialized)
                    f.flush()

                    # 3. Measure physical os.fsync Latency
                    t0 = time.perf_counter()
                    os.fsync(fd)
                    t_fsync_list.append((time.perf_counter() - t0) * 1000.0)
                finally:
                    fcntl.flock(fd, fcntl.LOCK_UN)

        p50_ser, p95_ser, _ = self._calculate_percentiles(t_serialize_list)
        p50_lock, p95_lock, _ = self._calculate_percentiles(t_flock_list)
        p50_sync, p95_sync, _ = self._calculate_percentiles(t_fsync_list)

        print("\n" + "=" * 60)
        print(" [B.3.1 Benchmark] 3. Cost Decomposition (P50 / P95)")
        print("=" * 60)
        print(f" Serialization (T_ser):   P50 = {p50_ser:.4f} ms | P95 = {p95_ser:.4f} ms")
        print(f" Lock Acquisition (T_lock): P50 = {p50_lock:.4f} ms | P95 = {p95_lock:.4f} ms")
        print(f" Physical Disk (T_fsync):  P50 = {p50_sync:.4f} ms | P95 = {p95_sync:.4f} ms")
        print("=" * 60)
        print(" Decision Record Conclusion:")
        if p50_sync > p50_ser + p50_lock:
            print(" -> Physical os.fsync Disk I/O is the DOMINANT latency bottleneck.")
        else:
            print(" -> CPU Serialization / Lock acquisition dominates latency.")
        print("=" * 60)


if __name__ == "__main__":
    unittest.main()
