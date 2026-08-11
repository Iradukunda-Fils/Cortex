#!/usr/bin/env python3
"""
Issue #11 Fault & Crash Semantics Research Script

Executes Scenarios A through F and generates docs/operations/crash_semantics_report.json.
"""

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cortex._research.crash_semantics import generate_crash_semantics_report


def main() -> None:
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "operations", "crash_semantics_report.json")
    print("🔬 Running Cortex Issue #11 Plugin Crash Semantics Research Suite...")
    results = generate_crash_semantics_report(output_path)

    print("\n=================================================================")
    print("          ISSUE #11 PLUGIN CRASH & FAILURE SEMANTICS REPORT       ")
    print("=================================================================")
    print(f"Environment: Python {results['environment']['python_version']} on {results['environment']['os']} ({results['environment']['arch']})")
    print("-----------------------------------------------------------------")
    for key, sc in results["scenarios"].items():
        print(f"[{sc['title']}]")
        final_st = sc.get("final_state") or f"WF1: {sc.get('workflow_1_final_state')}, WF2: {sc.get('workflow_2_final_state')}"
        print(f"  - Host Survived: {sc['host_survived']} | Final State: {final_st}")
        if "error_type" in sc and sc["error_type"]:
            print(f"  - Error Type: {sc['error_type']} | Message: {sc.get('error_message')}")
        if "stage_c_executed" in sc:
            print(f"  - Prior Events Preserved: {sc['prior_events_preserved_in_store']} | Stage C Executed: {sc['stage_c_executed']}")
        if "subsequent_workflow_isolated" in sc:
            print(f"  - Isolated: {sc['subsequent_workflow_isolated']}")
    print("-----------------------------------------------------------------")
    print("Single-Process Limitations Identified:")
    for lim in results["summary"]["single_process_limitations"]:
        print(f"  • {lim}")
    print("=================================================================")
    print(f"[✓] Artifact generated cleanly: {output_path}\n")


if __name__ == "__main__":
    main()
