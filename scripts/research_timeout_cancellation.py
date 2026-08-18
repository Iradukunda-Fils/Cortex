#!/usr/bin/env python3
"""
Issue #12 Timeout & Cancellation Semantics Research Script

Executes Scenarios A through G and generates docs/operations/timeout_cancellation_report.json.
"""

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cortex._research.timeout_cancellation import generate_timeout_cancellation_report


def main() -> None:
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research", "fault-tolerance", "timeout_cancellation_report.json")
    print("🔬 Running Cortex Issue #12 Timeout & Cancellation Semantics Research Suite...")
    results = generate_timeout_cancellation_report(output_path)

    print("\n=================================================================")
    print("        ISSUE #12 WORKFLOW TIMEOUT & CANCELLATION REPORT          ")
    print("=================================================================")
    print(f"Environment: Python {results['environment']['python_version']} on {results['environment']['os']} ({results['environment']['arch']})")
    print("-----------------------------------------------------------------")
    for key, sc in results["scenarios"].items():
        print(f"[{sc['title']}]")
        if "final_state" in sc:
            print(f"  - Final State: {sc['final_state']}")
        if "downstream_stage_3_halted" in sc:
            print(f"  - Stage 1 Preserved: {sc['stage_1_events_preserved']} | Downstream Halted: {sc['downstream_stage_3_halted']}")
        if "main_thread_blocked_sec" in sc:
            print(f"  - Thread Blocked: {sc['main_thread_blocked_sec']}s | Limiter: {sc['single_process_limitation']}")
        if "subsequent_workflow_healthy" in sc:
            print(f"  - WF1: {sc['workflow_1_final_state']} | WF2: {sc['workflow_2_final_state']} | Healthy: {sc['subsequent_workflow_healthy']}")
        if "deterministic_cancellation" in sc:
            print(f"  - Iterations: {sc['iteration_count']} | Deterministic: {sc['deterministic_cancellation']}")
    print("-----------------------------------------------------------------")
    print("Key Architectural Finding for v0.3 Decision:")
    print(f"  • {results['summary']['key_architectural_finding']}")
    print("=================================================================")
    print(f"[✓] Artifact generated cleanly: {output_path}\n")


if __name__ == "__main__":
    main()
