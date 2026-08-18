#!/usr/bin/env python3
"""
Issue #10 Benchmark Runner

Executes the internal telemetry benchmark harness across N=30 runs for Workloads A, B, and C
and generates docs/operations/telemetry_research_report.json.
"""

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cortex._telemetry.benchmark import generate_research_report


def main() -> None:
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research", "telemetry", "telemetry_research_report.json")
    print("🚀 Running Cortex Issue #10 Benchmark Harness (N=30 samples)...")
    results = generate_research_report(output_path, sample_count=30)

    print("\n=================================================================")
    print("           ISSUE #10 RUNTIME TELEMETRY RESEARCH BENCHMARK          ")
    print("=================================================================")
    print(f"Sample Count: {results['sample_count_per_workload']} runs per workload")
    print(f"Environment:  Python {results['environment']['python_version']} on {results['environment']['os']} ({results['environment']['arch']})")
    print("-----------------------------------------------------------------")
    wa = results['workload_a']
    wb = results['workload_b']
    wc = results['workload_c']

    print("Workload A (Baseline Single-Plugin):")
    print(f"  - Events: {wa['event_count']} | State: {wa['state_transitions'][-1]}")
    print(f"  - P50: {wa['p50_ms']:.4f} ms | P95: {wa['p95_ms']:.4f} ms | P99: {wa['p99_ms']:.4f} ms | Mean: {wa['mean_ms']:.4f} ms")
    print("Workload B (Multi-Stage 3-Plugin Chained Events):")
    print(f"  - Events: {wb['event_count']} | State: {wb['state_transitions'][-1]}")
    print(f"  - P50: {wb['p50_ms']:.4f} ms | P95: {wb['p95_ms']:.4f} ms | P99: {wb['p99_ms']:.4f} ms | Mean: {wb['mean_ms']:.4f} ms")
    print("Workload C (Capability Violation Failure):")
    print(f"  - Events: {wc['event_count']} | State: {wc['state_transitions'][-1]} | Violations: {wc['verification_violations']}")
    print(f"  - P50: {wc['p50_ms']:.4f} ms | P95: {wc['p95_ms']:.4f} ms | P99: {wc['p99_ms']:.4f} ms | Mean: {wc['mean_ms']:.4f} ms")
    print("=================================================================")
    print(f"[✓] Artifact generated cleanly: {output_path}\n")


if __name__ == "__main__":
    main()
