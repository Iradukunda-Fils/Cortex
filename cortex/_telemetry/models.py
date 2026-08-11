"""
Internal Telemetry Schemas & Serialization Models
"""

import statistics
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PluginInvocationMetric:
    """Plugin operational execution metric."""
    plugin_name: str
    invocations: int = 0
    total_duration_ms: float = 0.0
    successes: int = 0
    failures: int = 0


@dataclass
class WorkflowTelemetryRecord:
    """Telemetry record for a single workflow execution."""
    workflow_id: str
    name: str
    goal: str
    final_state: str
    total_duration_ms: float
    event_count: int
    state_transitions: list[str] = field(default_factory=list)
    event_types: list[str] = field(default_factory=list)
    verification_passed_count: int = 0
    verification_failed_count: int = 0
    capability_violation_count: int = 0
    lineage_intact: bool = True
    plugin_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class WorkloadBenchmarkSummary:
    """Statistical summary for repeated N-run benchmark executions."""
    workload_name: str
    sample_count: int
    environment: dict[str, str]
    duration_samples_ms: list[float]
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    min_ms: float
    max_ms: float
    stdev_ms: float
    event_count: int
    state_transitions: list[str]
    verification_violations: int

    def to_dict(self) -> dict[str, Any]:
        """Convert benchmark summary to JSON-serializable dictionary."""
        return asdict(self)


def calculate_quantiles(samples: list[float]) -> tuple[float, float, float, float, float, float, float]:
    """Computes (p50, p95, p99, mean, min_val, max_val, stdev) from float samples."""
    if not samples:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    sorted_samples = sorted(samples)
    n = len(sorted_samples)

    def percentile(p: float) -> float:
        if n == 1:
            return sorted_samples[0]
        k = (n - 1) * (p / 100.0)
        f = int(k)
        c = f + 1
        if c >= n:
            return sorted_samples[-1]
        d0 = sorted_samples[f] * (c - k)
        d1 = sorted_samples[c] * (k - f)
        return d0 + d1

    p50 = percentile(50.0)
    p95 = percentile(95.0)
    p99 = percentile(99.0)
    mean_val = statistics.mean(sorted_samples)
    min_val = sorted_samples[0]
    max_val = sorted_samples[-1]
    stdev_val = statistics.stdev(sorted_samples) if n > 1 else 0.0

    return p50, p95, p99, mean_val, min_val, max_val, stdev_val
