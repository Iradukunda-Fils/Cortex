"""
Thin CLI Adapter Engine for Cortex Platform

Delegates workflow lifecycle execution, trace inspection, and deterministic
replay directly to the public CortexClient API. Contains zero state machine logic.
"""

import json
import os
from typing import cast
from cortex.client import CortexClient
from cortex.schema import IntentEvent, WorkflowPolicy


def run_workflow_file(workflow_file: str, output_file: str | None = None) -> dict[str, str | int]:
    """Runs a workflow file by instantiating CortexClient thin wrapper."""
    if not os.path.exists(workflow_file):
        raise FileNotFoundError(f"Workflow file not found: {workflow_file}")

    with open(workflow_file, "r", encoding="utf-8") as f:
        if workflow_file.endswith(".yaml") or workflow_file.endswith(".yml"):
            import yaml
            data = cast(dict[str, object], yaml.safe_load(f)) or {}
        else:
            data = cast(dict[str, object], json.load(f))

    client = CortexClient()

    wf_name = str(data.get("name", "cli_workflow"))
    wf_goal = str(data.get("goal", "Execute CLI workflow"))
    policy_data = cast(dict[str, object], data.get("policy", {}))

    policy = WorkflowPolicy(
        timeout_seconds=float(str(policy_data.get("timeout_seconds", 300.0))),
        max_retries=int(str(policy_data.get("max_retries", 3))),
        abort_on_verification_failure=bool(policy_data.get("abort_on_verification_failure", True)),
    )

    workflow = client.create_workflow(name=wf_name, goal=wf_goal, policy=policy)

    intent_data = cast(dict[str, object], data.get("initial_intent", {}))
    initial_intent = IntentEvent(
        workflow_id=workflow.workflow_id,
        goal=str(intent_data.get("goal", wf_goal)),
        parameters=cast(dict[str, object], intent_data.get("parameters", {})),
    )

    executed_wf = client.run_workflow(workflow, initial_intent=initial_intent)

    if output_file is None:
        cortex_dir = os.path.join(os.getcwd(), ".cortex", "events")
        output_file = os.path.join(cortex_dir, f"{executed_wf.workflow_id}.json")

    saved_path = client.save_trace(executed_wf.workflow_id, output_file, name=wf_name, goal=wf_goal)

    return {
        "workflow_id": executed_wf.workflow_id,
        "state": executed_wf.state.value,
        "event_count": len(client.event_store.get_log()),
        "output_file": saved_path,
    }


def inspect_workflow(trace_path_or_id: str) -> dict[str, str | int | list[str] | list[dict[str, object]]]:
    """Delegates trace inspection to CortexClient."""
    client = CortexClient()
    res = client.inspect_workflow(trace_path_or_id)
    causality_tree = cast(list[str], res.get("causality_tree", []))
    failed_nodes = cast(list[dict[str, object]], res.get("failed_nodes", []))

    return {
        "workflow_id": trace_path_or_id,
        "name": cast(str, res.get("name", "Inspected Workflow")),
        "goal": cast(str, res.get("goal", "Trace Inspection")),
        "state": "FAILED" if failed_nodes else "COMPLETED",
        "node_count": cast(int, res.get("node_count", 0)),
        "total_events": cast(int, res.get("total_events", 0)),
        "causality_tree": causality_tree,
        "failed_nodes": failed_nodes,
    }


def replay_workflow(trace_path_or_id: str) -> dict[str, str | int | bool]:
    """Delegates trace replay to CortexClient."""
    client = CortexClient()
    res = client.replay_workflow(trace_path_or_id)
    return {
        "workflow_id": trace_path_or_id,
        "events_replayed": cast(int, res.get("replayed_count", 0)),
        "deterministic": cast(bool, res.get("deterministic", False)),
        "verification_result": cast(str, res.get("reason", "")),
    }
