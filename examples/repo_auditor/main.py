"""
Autonomous Repository Auditor External Application Entrypoint
"""

import argparse
import sys
from typing import cast

from cortex import CortexClient, WorkflowState
from examples.repo_auditor.plugins import (
    AuditorExecutorPlugin,
    AuditorPlannerPlugin,
    ReadOnlyRepoToolPlugin,
)


def run_repo_auditor(simulate_violation: bool = False) -> int:
    """Executes the Autonomous Repository Auditor Application."""
    print("==================================================================")
    print("       Cortex v0.2 Dogfood App: Autonomous Repository Auditor     ")
    print("==================================================================")

    # 1. Instantiate public CortexClient with platform capability grants
    platform_caps = {
        "workflow.plan.create",
        "workflow.command.issue",
        "fs:read",
        "exec:git",
        "exec:pytest",
        "hardware.telemetry.read",
    }
    client = CortexClient(platform_capabilities=platform_caps)

    # 2. Instantiate and Register External Plugins
    planner = AuditorPlannerPlugin()
    executor = AuditorExecutorPlugin()
    repo_tool = ReadOnlyRepoToolPlugin(simulate_sandbox_violation=simulate_violation)

    _ = client.register_plugin(planner)
    _ = client.register_plugin(executor)
    _ = client.register_plugin(repo_tool)

    # 3. Create and Run Workflow
    workflow = client.create_workflow(
        name="repo_audit_workflow",
        goal="Audit Repository Integrity",
    )

    print(f"[+] Triggering Audit Workflow (ID: {workflow.workflow_id[:8]}...)...")
    executed_wf = client.run_workflow(workflow)

    print(f"\n[+] Workflow Execution Final State: {executed_wf.state.value}")

    # 4. Save and Inspect Trace
    trace_path = f".cortex/events/{executed_wf.workflow_id}.json"
    _ = client.save_trace(executed_wf.workflow_id, trace_path)

    inspection = client.inspect_workflow(trace_path)
    causality_tree = cast(list[str], inspection["causality_tree"])
    failed_nodes = cast(list[dict[str, object]], inspection["failed_nodes"])

    print("\n--- Execution Causality Tree ---")
    for line in causality_tree:
        print(f"  {line}")

    if failed_nodes:
        print(f"\n[!] Verification Failures ({len(failed_nodes)}):")
        for node in failed_nodes:
            print(f"    - Failure Node ID: {str(node['id'])[:8]} | Payload: {node['payload']}")
    else:
        print("\n[✓] All Verification Invariants Passed Cleanly!")

    # 5. Deterministic Replay Verification
    replay_res = client.replay_workflow(trace_path)
    print("\n--- Deterministic Replay Engine ---")
    print(f"Events Replayed: {replay_res['replayed_count']}")
    print(f"Result Status:   {'PASSED' if replay_res['deterministic'] else 'FAILED'}")
    print(f"Lineage Reason:  {replay_res['reason']}")

    if simulate_violation:
        if executed_wf.state == WorkflowState.FAILED and failed_nodes:
            print(
                "\n[✓] PROOF PASSED: CapabilitySandbox successfully intercepted and rejected unauthorized write invocation!"
            )
            return 0
        else:
            print("\n[!] ERROR: Expected workflow FAILED state for sandbox violation, but got PASS.")
            return 1

    return 0 if executed_wf.state == WorkflowState.COMPLETED else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous Repository Auditor Dogfood App")
    _ = parser.add_argument(
        "--simulate-violation",
        action="store_true",
        help="Simulate unauthorized capability write violation",
    )
    args = parser.parse_args()
    simulate_violation_flag = bool(getattr(args, "simulate_violation", False))
    sys.exit(run_repo_auditor(simulate_violation=simulate_violation_flag))


if __name__ == "__main__":
    main()
