"""
Cortex v0.3 Dogfood Harness: Controlled Synthetic Workload Profiler

Runs the Repo Auditor pipeline with 5 controlled synthetic workload profiles,
collecting operational metrics (duration, events, memory, replay, trace size).

IMPORTANT: These workloads measure Cortex runtime overhead (event propagation,
EventStore journaling, capability enforcement, replay determinism). The Repo
Auditor plugins produce synthetic results — they do NOT perform real repository
analysis. Do not interpret these measurements as repository analysis benchmarks.

Usage:
    uv run python -m examples.repo_auditor.dogfood_harness
"""

import json
import os
import platform
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass, field
from typing import cast

from cortex import (
    BaseEvent,
    CommandIssuedEvent,
    CortexClient,
    DriverTelemetryEvent,
    IntentEvent,
    PlanGeneratedEvent,
    VerificationResultEvent,
)
from examples.repo_auditor.plugins.configurable_planner import ConfigurablePlannerPlugin
from examples.repo_auditor.plugins.executor import AuditorExecutorPlugin
from examples.repo_auditor.plugins.repo_tool import ReadOnlyRepoToolPlugin

# ---------------------------------------------------------------------------
# Named Constants — Workload Profile Sizes
# ---------------------------------------------------------------------------

PROFILE_MINIMAL_STEPS = 3
PROFILE_STANDARD_STEPS = 10
PROFILE_LARGE_STEPS = 50
PROFILE_STRESS_STEPS = 200
PROFILE_VIOLATION_STEPS = 3

# Cortex version from pyproject.toml
CORTEX_VERSION = "0.3.0rc1"

# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------


@dataclass
class PhaseTimings:
    """Wall-clock durations for each execution phase (seconds)."""

    registration_s: float = 0.0
    execution_s: float = 0.0
    trace_save_s: float = 0.0
    inspect_s: float = 0.0
    replay_s: float = 0.0
    total_s: float = 0.0


@dataclass
class EventBreakdown:
    """Event counts by type."""

    total: int = 0
    intent: int = 0
    plan: int = 0
    command: int = 0
    telemetry: int = 0
    verification_pass: int = 0
    verification_fail: int = 0
    capability_violation: int = 0
    other: int = 0


@dataclass
class MemoryMetrics:
    """Memory usage metrics.

    Measured via Python tracemalloc (tracks Python memory allocations only,
    NOT total process RSS). Peak represents the maximum tracked allocation
    during the profiled execution window.
    """

    peak_traced_mb: float = 0.0
    current_traced_mb: float = 0.0
    measurement_method: str = "tracemalloc (Python allocations only)"


@dataclass
class CapabilityMetrics:
    """Capability negotiation results."""

    requested: list[str] = field(default_factory=list)
    granted: list[str] = field(default_factory=list)
    denied: list[str] = field(default_factory=list)
    violation_count: int = 0


@dataclass
class ReplayResult:
    """Replay execution and equivalence results."""

    executed_successfully: bool = False
    proven_equivalent: bool = False
    events_replayed: int = 0
    reason: str = ""


@dataclass
class EnvironmentMetadata:
    """Runtime environment information."""

    python_version: str = ""
    cortex_version: str = ""
    os_name: str = ""
    os_version: str = ""
    architecture: str = ""
    uv_version: str = ""


@dataclass
class ProfileResult:
    """Complete metrics for a single controlled synthetic workload profile."""

    profile_name: str = ""
    profile_description: str = ""
    step_count: int = 0
    workload_type: str = "synthetic"
    workflow_state: str = ""
    timestamp_iso: str = ""
    timings: PhaseTimings = field(default_factory=PhaseTimings)
    events: EventBreakdown = field(default_factory=EventBreakdown)
    memory: MemoryMetrics = field(default_factory=MemoryMetrics)
    trace_size_bytes: int = 0
    replay: ReplayResult = field(default_factory=ReplayResult)
    capabilities: CapabilityMetrics = field(default_factory=CapabilityMetrics)
    plugin_count: int = 0
    events_per_second: float = 0.0
    environment: EnvironmentMetadata = field(default_factory=EnvironmentMetadata)


# ---------------------------------------------------------------------------
# Workload Profiles (Named Constants, NOT magic numbers)
# ---------------------------------------------------------------------------

WORKLOAD_PROFILES: list[dict[str, object]] = [
    {
        "name": "minimal",
        "steps": PROFILE_MINIMAL_STEPS,
        "description": "Baseline synthetic workload (small utility library scale)",
        "violation": False,
    },
    {
        "name": "standard",
        "steps": PROFILE_STANDARD_STEPS,
        "description": "Normal synthetic workload (medium web framework scale)",
        "violation": False,
    },
    {
        "name": "large",
        "steps": PROFILE_LARGE_STEPS,
        "description": "Scaling synthetic workload (large monorepo scale)",
        "violation": False,
    },
    {
        "name": "stress",
        "steps": PROFILE_STRESS_STEPS,
        "description": "Stress synthetic workload (enterprise codebase scale)",
        "violation": False,
    },
    {
        "name": "violation",
        "steps": PROFILE_VIOLATION_STEPS,
        "description": "Capability enforcement test (sandbox security path)",
        "violation": True,
    },
]


# ---------------------------------------------------------------------------
# Environment Collector
# ---------------------------------------------------------------------------


def collect_environment() -> EnvironmentMetadata:
    """Collect runtime environment metadata."""
    return EnvironmentMetadata(
        python_version=platform.python_version(),
        cortex_version=CORTEX_VERSION,
        os_name=platform.system(),
        os_version=platform.release(),
        architecture=platform.machine(),
    )


# ---------------------------------------------------------------------------
# Profile Runner
# ---------------------------------------------------------------------------


def run_profile(profile: dict[str, object], output_dir: str) -> ProfileResult:
    """Execute a single controlled synthetic workload profile and collect metrics."""
    name = str(profile["name"])
    steps = int(str(profile["steps"]))
    violation = bool(profile["violation"])
    description = str(profile.get("description", name))

    result = ProfileResult(
        profile_name=name,
        profile_description=description,
        step_count=steps,
        workload_type="synthetic",
        timestamp_iso=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        environment=collect_environment(),
    )

    # Start memory tracking (Python allocations only)
    tracemalloc.start()

    total_start = time.perf_counter()

    # --- Phase 1: Registration ---
    reg_start = time.perf_counter()

    platform_caps = {
        "workflow.plan.create",
        "workflow.command.issue",
        "fs:read",
        "exec:git",
        "exec:pytest",
        "hardware.telemetry.read",
    }
    client = CortexClient(platform_capabilities=platform_caps)

    planner = ConfigurablePlannerPlugin(step_count=steps)
    executor = AuditorExecutorPlugin()
    repo_tool = ReadOnlyRepoToolPlugin(simulate_sandbox_violation=violation)

    reg_planner = client.register_plugin(planner)
    reg_executor = client.register_plugin(executor)
    reg_repo_tool = client.register_plugin(repo_tool)

    result.plugin_count = len(client.registered_plugins)
    result.timings.registration_s = time.perf_counter() - reg_start

    # Collect capability metrics
    for reg in [reg_planner, reg_executor, reg_repo_tool]:
        result.capabilities.requested.extend(reg.manifest.required_capabilities)
        result.capabilities.granted.extend(reg.granted_capabilities)
        result.capabilities.denied.extend(reg.denied_capabilities)

    # --- Phase 2: Execution ---
    exec_start = time.perf_counter()

    workflow = client.create_workflow(
        name=f"dogfood_{name}",
        goal=f"Synthetic workload: {description}",
    )
    executed = client.run_workflow(workflow)
    result.workflow_state = executed.state.value
    result.timings.execution_s = time.perf_counter() - exec_start

    # --- Phase 3: Trace Save ---
    save_start = time.perf_counter()

    trace_path = os.path.join(output_dir, f"trace_{name}.json")
    _ = client.save_trace(
        executed.workflow_id,
        trace_path,
        name=f"dogfood_{name}",
        goal=description,
    )
    result.timings.trace_save_s = time.perf_counter() - save_start

    # --- Phase 4: Inspect ---
    inspect_start = time.perf_counter()
    _ = client.inspect_workflow(trace_path)
    result.timings.inspect_s = time.perf_counter() - inspect_start

    # --- Phase 5: Replay ---
    replay_start = time.perf_counter()
    replay_res = client.replay_workflow(trace_path)
    result.timings.replay_s = time.perf_counter() - replay_start

    replay_deterministic = cast(bool, replay_res.get("deterministic", False))
    replay_count = cast(int, replay_res.get("replayed_count", 0))
    replay_reason = cast(str, replay_res.get("reason", ""))

    result.replay = ReplayResult(
        executed_successfully=True,
        proven_equivalent=replay_deterministic,
        events_replayed=replay_count,
        reason=replay_reason,
    )

    # --- Total ---
    result.timings.total_s = time.perf_counter() - total_start

    # --- Event Breakdown ---
    events = client.event_store.get_log()
    result.events.total = len(events)
    for e in events:
        if isinstance(e, IntentEvent):
            result.events.intent += 1
        elif isinstance(e, PlanGeneratedEvent):
            result.events.plan += 1
        elif isinstance(e, CommandIssuedEvent):
            result.events.command += 1
        elif isinstance(e, DriverTelemetryEvent):
            result.events.telemetry += 1
        elif isinstance(e, VerificationResultEvent):
            if e.passed:
                result.events.verification_pass += 1
            else:
                result.events.verification_fail += 1
                if e.rule_id == "CAPABILITY_VIOLATION":
                    result.events.capability_violation += 1
                    result.capabilities.violation_count += 1
        elif isinstance(e, BaseEvent):
            result.events.other += 1

    # --- Memory (tracemalloc = Python allocations only) ---
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result.memory.current_traced_mb = round(current / (1024 * 1024), 3)
    result.memory.peak_traced_mb = round(peak / (1024 * 1024), 3)

    # --- Trace Size ---
    if os.path.exists(trace_path):
        result.trace_size_bytes = os.path.getsize(trace_path)

    # --- Throughput ---
    if result.timings.execution_s > 0:
        result.events_per_second = round(result.events.total / result.timings.execution_s, 1)
    else:
        result.events_per_second = float(result.events.total)

    return result


# ---------------------------------------------------------------------------
# Harness Entrypoint
# ---------------------------------------------------------------------------


def run_dogfood_harness(output_base: str | None = None) -> list[ProfileResult]:
    """Execute all controlled synthetic workload profiles and save telemetry."""
    if output_base is None:
        output_base = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "docs",
            "operations",
            "dogfood_results",
        )
    output_base = os.path.abspath(output_base)
    os.makedirs(output_base, exist_ok=True)

    print("=" * 70)
    print("  Cortex v0.3 Dogfood Harness: Controlled Synthetic Workloads")
    print("=" * 70)
    print(f"  Output: {output_base}")
    print()

    results: list[ProfileResult] = []

    for profile in WORKLOAD_PROFILES:
        name = str(profile["name"])
        steps = int(str(profile["steps"]))
        desc = str(profile.get("description", ""))

        print(f"  [{name.upper()}] {steps}-step synthetic workload ({desc})...", end=" ", flush=True)

        result = run_profile(profile, output_base)
        results.append(result)

        status = "✓" if result.workflow_state in ("COMPLETED", "FAILED") else "✗"
        replay_status = "EQUIVALENT" if result.replay.proven_equivalent else "NOT EQUIVALENT"
        print(
            f"{status} {result.workflow_state} | "
            f"{result.events.total} events | "
            f"{result.timings.total_s:.4f}s | "
            f"replay={replay_status}"
        )

    # Save aggregate results with environment metadata
    aggregate_path = os.path.join(output_base, "aggregate_results.json")
    aggregate = [asdict(r) for r in results]
    with open(aggregate_path, "w", encoding="utf-8") as f:
        json.dump(aggregate, f, indent=2)

    print()
    print(f"  Raw telemetry saved to: {aggregate_path}")
    print("=" * 70)

    return results


def main() -> None:
    """CLI entrypoint."""
    results = run_dogfood_harness()

    # Print summary table
    print()
    print(
        f"  {'Profile':<12} {'Steps':>6} {'Events':>7} {'Duration':>10} "
        f"{'Evt/s':>8} {'Memory':>10} {'Trace':>8} {'Replay':>12} {'State':<10}"
    )
    print("  " + "-" * 96)

    for r in results:
        trace_kb = round(r.trace_size_bytes / 1024, 1)
        replay_str = "EQUIVALENT" if r.replay.proven_equivalent else "DIVERGENT"
        print(
            f"  {r.profile_name:<12} {r.step_count:>6} {r.events.total:>7} "
            f"{r.timings.total_s:>9.4f}s {r.events_per_second:>7.1f} "
            f"{r.memory.peak_traced_mb:>8.2f}MB {trace_kb:>6.1f}KB "
            f"{replay_str:>12} {r.workflow_state:<10}"
        )

    # Check all passed
    all_ok = all(r.workflow_state in ("COMPLETED", "FAILED") and r.replay.proven_equivalent for r in results)
    print()
    if all_ok:
        print("  [✓] All 5 controlled synthetic workload profiles executed successfully.")
        print("  [✓] Replay equivalence proven for all profiles.")
    else:
        print("  [✗] Some profiles failed verification.")
        sys.exit(1)


if __name__ == "__main__":
    main()
