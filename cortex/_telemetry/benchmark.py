"""
Repeatable Runtime Benchmark Harness for Operational Research

Executes Workloads A (Baseline), B (Multi-Stage), and C (Capability Failure)
over N >= 30 iterations to calculate P50, P95, and P99 latency statistics.
"""

import json
import os
import platform
import sys
import time
from typing import Any

from cortex import (
    BaseEvent,
    BasePlugin,
    CommandIssuedEvent,
    CortexClient,
    DriverTelemetryEvent,
    IntentEvent,
    PlanGeneratedEvent,
    PluginManifest,
)
from cortex._telemetry.collector import TelemetryCollector
from cortex._telemetry.models import WorkloadBenchmarkSummary, calculate_quantiles
from cortex.compat import override


# --- Workload A Plugins ---
class BaselinePlannerPlugin(BasePlugin):
    """Simple single-stage planner plugin."""

    def __init__(self) -> None:
        manifest = PluginManifest(
            name="baseline-planner",
            version="1.0.0",
            description="Baseline single-stage planner",
            consumes_events=["IntentEvent"],
            produces_events=["PlanGeneratedEvent"],
            required_capabilities=["workflow.plan.create"],
        )
        super().__init__(manifest)

    @override
    def on_event(self, event: BaseEvent) -> None:
        if isinstance(event, IntentEvent) and self.context:
            self.context.publish(PlanGeneratedEvent(
                workflow_id=event.workflow_id,
                intent_id=event.intent_id,
                causation_id=event.event_id,
                steps=[{"step": 1, "action": "baseline_action"}],
            ))


# --- Workload B Plugins ---
class MultiStagePlannerPlugin(BasePlugin):
    """Multi-stage planner plugin (Stage 1)."""

    def __init__(self) -> None:
        manifest = PluginManifest(
            name="multistage-planner",
            version="1.0.0",
            description="Multi-stage planner",
            consumes_events=["IntentEvent"],
            produces_events=["PlanGeneratedEvent"],
            required_capabilities=["workflow.plan.create"],
        )
        super().__init__(manifest)

    @override
    def on_event(self, event: BaseEvent) -> None:
        if isinstance(event, IntentEvent) and self.context:
            self.context.publish(PlanGeneratedEvent(
                workflow_id=event.workflow_id,
                intent_id=event.intent_id,
                causation_id=event.event_id,
                steps=[
                    {"step": 1, "action": "stage_1"},
                    {"step": 2, "action": "stage_2"},
                ],
            ))


class MultiStageDispatcherPlugin(BasePlugin):
    """Multi-stage dispatcher plugin (Stage 2)."""

    def __init__(self) -> None:
        manifest = PluginManifest(
            name="multistage-dispatcher",
            version="1.0.0",
            description="Multi-stage dispatcher",
            consumes_events=["PlanGeneratedEvent"],
            produces_events=["CommandIssuedEvent"],
            required_capabilities=["workflow.command.issue"],
        )
        super().__init__(manifest)

    @override
    def on_event(self, event: BaseEvent) -> None:
        if isinstance(event, PlanGeneratedEvent) and self.context:
            for step in event.steps:
                self.context.publish(CommandIssuedEvent(
                    workflow_id=event.workflow_id,
                    command_id=f"cmd_{step.get('step', 1)}",
                    causation_id=event.event_id,
                    action=str(step.get("action", "exec")),
                ))


class MultiStageExecutorPlugin(BasePlugin):
    """Multi-stage executor telemetry plugin (Stage 3)."""

    def __init__(self) -> None:
        manifest = PluginManifest(
            name="multistage-executor",
            version="1.0.0",
            description="Multi-stage executor",
            consumes_events=["CommandIssuedEvent"],
            produces_events=["DriverTelemetryEvent"],
            required_capabilities=["driver.telemetry.read"],
        )
        super().__init__(manifest)

    @override
    def on_event(self, event: BaseEvent) -> None:
        if isinstance(event, CommandIssuedEvent) and self.context:
            self.context.publish(DriverTelemetryEvent(
                workflow_id=event.workflow_id,
                driver_id="driver_01",
                causation_id=event.event_id,
                status="SUCCESS",
                payload={"action": event.action},
            ))


# --- Workload C Plugins ---
class UnauthorizedCapPlugin(BasePlugin):
    """Plugin requesting forbidden capability."""

    def __init__(self) -> None:
        manifest = PluginManifest(
            name="unauthorized-cap-plugin",
            version="1.0.0",
            description="Unauthorized plugin",
            consumes_events=["IntentEvent"],
            produces_events=[],
            required_capabilities=["sys.unauthorized_access"],
        )
        super().__init__(manifest)

    @override
    def on_event(self, event: BaseEvent) -> None:
        pass


def run_benchmark_suite(sample_count: int = 30) -> dict[str, Any]:
    """Executes N repeated benchmark samples for Workloads A, B, and C."""
    env_metadata = {
        "python_version": sys.version.split()[0],
        "os": platform.system(),
        "release": platform.release(),
        "arch": platform.machine(),
    }

    # --- Workload A: Baseline ---
    samples_a: list[float] = []
    events_a = 0
    transitions_a: list[str] = []

    for i in range(sample_count):
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(BaselinePlannerPlugin())
        wf = client.create_workflow(name=f"baseline_wf_{i}", goal="Baseline Goal")
        collector = TelemetryCollector(client)

        start_ns = time.perf_counter_ns()
        executed_wf = client.run_workflow(wf)
        end_ns = time.perf_counter_ns()

        rec = collector.collect_workflow_metrics(executed_wf, start_ns, end_ns)
        samples_a.append(rec.total_duration_ms)
        if i == 0:
            events_a = rec.event_count
            transitions_a = rec.state_transitions

    p50_a, p95_a, p99_a, mean_a, min_a, max_a, stdev_a = calculate_quantiles(samples_a)
    summary_a = WorkloadBenchmarkSummary(
        workload_name="Workload A (Baseline Single-Plugin)",
        sample_count=sample_count,
        environment=env_metadata,
        duration_samples_ms=samples_a,
        p50_ms=p50_a,
        p95_ms=p95_a,
        p99_ms=p99_a,
        mean_ms=mean_a,
        min_ms=min_a,
        max_ms=max_a,
        stdev_ms=stdev_a,
        event_count=events_a,
        state_transitions=transitions_a,
        verification_violations=0,
    )

    # --- Workload B: Multi-Stage ---
    samples_b: list[float] = []
    events_b = 0
    transitions_b: list[str] = []

    for i in range(sample_count):
        client = CortexClient(platform_capabilities={"workflow.plan.create", "workflow.command.issue", "driver.telemetry.read"})
        _ = client.register_plugin(MultiStagePlannerPlugin())
        _ = client.register_plugin(MultiStageDispatcherPlugin())
        _ = client.register_plugin(MultiStageExecutorPlugin())

        wf = client.create_workflow(name=f"multistage_wf_{i}", goal="Multi-Stage Goal")
        collector = TelemetryCollector(client)

        start_ns = time.perf_counter_ns()
        executed_wf = client.run_workflow(wf)
        end_ns = time.perf_counter_ns()

        rec = collector.collect_workflow_metrics(executed_wf, start_ns, end_ns)
        samples_b.append(rec.total_duration_ms)
        if i == 0:
            events_b = rec.event_count
            transitions_b = rec.state_transitions

    p50_b, p95_b, p99_b, mean_b, min_b, max_b, stdev_b = calculate_quantiles(samples_b)
    summary_b = WorkloadBenchmarkSummary(
        workload_name="Workload B (Multi-Stage 3-Plugin Chained Events)",
        sample_count=sample_count,
        environment=env_metadata,
        duration_samples_ms=samples_b,
        p50_ms=p50_b,
        p95_ms=p95_b,
        p99_ms=p99_b,
        mean_ms=mean_b,
        min_ms=min_b,
        max_ms=max_b,
        stdev_ms=stdev_b,
        event_count=events_b,
        state_transitions=transitions_b,
        verification_violations=0,
    )

    # --- Workload C: Capability Failure ---
    samples_c: list[float] = []
    events_c = 0
    transitions_c: list[str] = []
    violations_c = 0

    for i in range(sample_count):
        client = CortexClient(platform_capabilities={"workflow.plan.create"})
        _ = client.register_plugin(UnauthorizedCapPlugin())

        wf = client.create_workflow(name=f"failure_wf_{i}", goal="Unauthorized Capability Goal")
        collector = TelemetryCollector(client)

        start_ns = time.perf_counter_ns()
        executed_wf = client.run_workflow(wf)
        end_ns = time.perf_counter_ns()

        rec = collector.collect_workflow_metrics(executed_wf, start_ns, end_ns)
        samples_c.append(rec.total_duration_ms)
        if i == 0:
            events_c = rec.event_count
            transitions_c = rec.state_transitions
            violations_c = rec.capability_violation_count

    p50_c, p95_c, p99_c, mean_c, min_c, max_c, stdev_c = calculate_quantiles(samples_c)
    summary_c = WorkloadBenchmarkSummary(
        workload_name="Workload C (Capability Violation Failure)",
        sample_count=sample_count,
        environment=env_metadata,
        duration_samples_ms=samples_c,
        p50_ms=p50_c,
        p95_ms=p95_c,
        p99_ms=p99_c,
        mean_ms=mean_c,
        min_ms=min_c,
        max_ms=max_c,
        stdev_ms=stdev_c,
        event_count=events_c,
        state_transitions=transitions_c,
        verification_violations=violations_c,
    )

    return {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sample_count_per_workload": sample_count,
        "environment": env_metadata,
        "workload_a": summary_a.to_dict(),
        "workload_b": summary_b.to_dict(),
        "workload_c": summary_c.to_dict(),
    }


def generate_research_report(output_filepath: str, sample_count: int = 30) -> dict[str, Any]:
    """Generates and writes the structured research JSON report."""
    results = run_benchmark_suite(sample_count=sample_count)

    os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    report_path = os.path.join("research", "telemetry", "telemetry_research_report.json")
    print("Executing Issue #10 benchmark suite (N=30 samples)...")
    res = generate_research_report(report_path, sample_count=30)
    print(f"Report written to {report_path}")
    print(f"Workload A P50: {res['workload_a']['p50_ms']:.4f} ms | P99: {res['workload_a']['p99_ms']:.4f} ms")
    print(f"Workload B P50: {res['workload_b']['p50_ms']:.4f} ms | P99: {res['workload_b']['p99_ms']:.4f} ms")
    print(f"Workload C P50: {res['workload_c']['p50_ms']:.4f} ms | P99: {res['workload_c']['p99_ms']:.4f} ms")
