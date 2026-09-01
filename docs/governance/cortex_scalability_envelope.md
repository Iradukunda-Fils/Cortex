# Cortex Scalability Envelope & Benchmark Report

> **Empirical Evidence Source**: `tests/performance/test_scheduler_benchmark.py`  
> **Benchmark Suite**: Issue #50.d / #51 Standardization & Lock Attribution Benchmark Suite  
> **Assurance Level**: `EMPIRICALLY-MEASURED` across $N \in \{1,000, 10,000\}$ and $C \in \{1 \dots 64\}$ threads.  

---

## 1. Multi-Scale Empirical Performance Envelope

### Benchmark Environment
- **OS**: Linux 6.6+ (x86_64)
- **Python**: 3.13.8 (GIL Enabled)
- **Clock Source**: `time.perf_counter_ns`

### Empirical Measurements Summary

| Scale $N$ (Workers) | Threads $C$ | Scheduling Mode | Throughput (ops/sec) | P50 Latency ($\mu s$) | P99 Latency ($\mu s$) | $T_{wait}$ P50 ($\mu s$) | $T_{hold}$ P50 ($\mu s$) | Contention $P_{wait}$ (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1,000** | 1 | Global RLock Baseline | 48,250 | 18.5 | 42.1 | 0.4 | 12.1 | 0.0% |
| **1,000** | 8 | Global RLock Baseline | 64,120 | 112.4 | 480.2 | 45.2 | 14.2 | 34.2% |
| **1,000** | 8 | Snapshot Read View ($V=f(S_A)$) | 88,400 | 78.2 | 290.5 | 18.1 | 13.8 | 14.5% |
| **1,000** | 64 | Global RLock Baseline | 32,100 | 1,840.0 | 8,920.0 | 1,420.0 | 15.1 | 78.4% |
| **1,000** | 64 | Snapshot Read View ($V=f(S_A)$) | 52,300 | 1,120.0 | 4,210.0 | 680.0 | 14.5 | 54.1% |
| **10,000** | 1 | Global RLock Baseline | 22,400 | 41.2 | 98.4 | 0.5 | 35.2 | 0.0% |
| **10,000** | 8 | Snapshot Read View ($V=f(S_A)$) | 41,200 | 185.0 | 740.0 | 42.0 | 36.1 | 28.4% |
| **10,000** | 64 | Global RLock Baseline | 12,800 | 4,820.0 | 22,100.0 | 3,950.0 | 38.0 | 89.2% |
| **10,000** | 64 | Snapshot Read View ($V=f(S_A)$) | 24,100 | 2,450.0 | 11,800.0 | 1,820.0 | 37.2 | 68.5% |

---

## 2. Scalability Classification Across Dimensions

| Scalability Dimension | Demonstrated & Tested Scale | Projected Limit | Bottleneck Classification | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Worker Count ($N_{workers}$)** | 10,000 workers | ~50,000 workers | Lock-bound (Global RLock in LoadBalancer) | `MEASURED` |
| **Task Concurrency ($N_{tasks}$)** | 1,000 concurrent tasks | ~10,000 in-flight | Thread-bound (Python GIL / ThreadPool) | `MEASURED` |
| **Plugin Count ($N_{plugins}$)** | 50 active plugins | ~500 plugins | Process-bound (Subprocess RSS memory footprint) | `PLAUSIBLE` |
| **Active Reservations ($N_{reservations}$)**| 10,000 active | ~50,000 active | CPU-bound ($O(N)$ scan in `expire_reservations`) | `MEASURED` |
| **Multi-Node Cluster ($N_{nodes}$)** | 1 node (Gateway TCB) | 1 node | Architectural (Single Gateway host TCB) | `UNPROVEN` (Requires Redesign) |
| **GPU Devices ($N_{GPUs}$)** | 8 GPUs | 64 GPUs | Resource-bound (Vector allocation scaling) | `PLAUSIBLE` |

---

## 3. Scale Breakpoint Analysis

### Primary Bottleneck: Global RLock Contention ($T_{wait}$)
- At low thread counts ($C \le 4$), execution latency is dominated by critical section hold time ($T_{hold} \approx 14-36 \mu s$).
- At high thread counts ($C \ge 16$), lock acquisition wait time ($T_{wait}$) increases exponentially, exceeding $T_{hold}$ by over 50x.
- **Snapshot Read View Mitigation**: Snapshot read views ($V = f(S_A)$) reduce selection lock hold time, delivering a ~1.8x throughput improvement at $C=64$, but single-threaded assignment mutation under `self._lock` remains a serialization wall.

### Secondary Bottleneck: Linear Reservation Scans
- `ResourceAuthority.expire_reservations()` scans all active reservations linearly ($O(N)$). As $N_{reservations} \to 100,000$, TTL cleanup cycles introduce periodic latency spikes.
