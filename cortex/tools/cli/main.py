"""
Cortex Developer CLI Command Entrypoint

Usage:
    cortex init <project_name> [--type {app|plugin}] [--json]
    cortex workflow run <workflow_file> [--output <file>] [--json]
    cortex workflow inspect <workflow_id_or_file> [--json]
    cortex workflow replay <workflow_id_or_file> [--json]
"""

import argparse
import json
import os
import sys
from collections.abc import Sequence
from typing import cast

from cortex.exceptions import (
    CapabilityViolationError,
    CortexError,
    ManifestError,
    WorkflowExecutionError,
)
from cortex.tools.cli.runner import inspect_workflow, replay_workflow, run_workflow_file
from cortex.tools.cli.scaffolder import scaffold_project


def _handle_cli_error(err: Exception, json_mode: bool = False) -> int:
    """Standardized CLI error renderer and exit code mapper.

    Outputs formatted diagnostic blocks or machine JSON strictly to sys.stderr.
    """
    if isinstance(err, CapabilityViolationError):
        error_code = "CAPABILITY_VIOLATION"
        exit_code = err.exit_code  # 2
        message = err.message
        cause = f"Action requested capability '{err.capability}' which was denied or not declared."
        remediation = f"Add capability '{err.capability}' to required_capabilities in your plugin manifest."
        details: dict[str, object] | None = {"capability": err.capability} if err.capability else None
    elif isinstance(err, ManifestError):
        error_code = "INVALID_MANIFEST"
        exit_code = err.exit_code  # 3
        message = err.message
        cause = "Plugin manifest failed structural validation checks."
        remediation = "Ensure plugin manifest contains non-empty 'name', 'version', and valid collections."
        details = None
    elif isinstance(err, WorkflowExecutionError):
        error_code = "WORKFLOW_FAILED"
        exit_code = err.exit_code  # 1
        message = err.message
        cause = "Workflow execution was aborted or failed verification checks."
        remediation = "Inspect trace log using 'cortex workflow inspect <trace>' for failed verification nodes."
        details = {"workflow_id": err.workflow_id} if err.workflow_id else None
    elif isinstance(err, CortexError):
        error_code = "CORTEX_ERROR"
        exit_code = err.exit_code  # 1
        message = err.message
        cause = "Cortex framework error occurred."
        remediation = "Verify workflow specification and input parameters."
        details = None
    else:
        error_code = "GENERAL_ERROR"
        exit_code = getattr(os, "EX_SOFTWARE", 1)
        message = str(err) or "An unexpected runtime error occurred."
        cause = f"Uncaught exception of type '{type(err).__name__}'."
        remediation = "Check environment setup, dependencies, and command line arguments."
        details = {"error_type": type(err).__name__}

    if json_mode:
        payload: dict[str, object] = {
            "status": "error",
            "error_code": error_code,
            "exit_code": exit_code,
            "message": message,
            "cause": cause,
            "remediation": remediation,
        }
        if details is not None:
            payload["details"] = details
        print(json.dumps(payload, indent=2), file=sys.stderr)
    else:
        print("=================================================================", file=sys.stderr)
        print("               CORTEX CLI DIAGNOSTIC ERROR REPORT                ", file=sys.stderr)
        print("=================================================================", file=sys.stderr)
        print(f"[!] ERROR CODE:   {error_code} (Exit Code {exit_code})", file=sys.stderr)
        print(f"[!] MESSAGE:      {message}", file=sys.stderr)
        print(f"[!] CAUSE:        {cause}", file=sys.stderr)
        print(f"[!] REMEDIATION:  {remediation}", file=sys.stderr)
        print("=================================================================", file=sys.stderr)

    return exit_code


def cli_entrypoint() -> None:
    """Console script entrypoint for PyPI cortex-runtime executable."""
    sys.exit(main())


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entrypoint for Cortex framework."""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="cortex",
        description="Cortex Platform Developer CLI & Workflow Engine",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON format",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # cortex init
    init_parser = subparsers.add_parser("init", help="Scaffold a new Cortex plugin or application")
    _ = init_parser.add_argument("project_name", help="Name of the project directory to create")
    _ = init_parser.add_argument(
        "--type",
        choices=["app", "plugin"],
        default="app",
        help="Type of project to scaffold (default: app)",
    )

    # cortex workflow
    wf_parser = subparsers.add_parser("workflow", help="Workflow execution and inspection management")
    wf_sub = wf_parser.add_subparsers(dest="wf_command", help="Workflow subcommand")

    # cortex workflow run
    wf_run = wf_sub.add_parser("run", help="Trigger workflow execution from spec file")
    _ = wf_run.add_argument("workflow_file", help="Path to workflow definition JSON file")
    _ = wf_run.add_argument("--output", "-o", help="Optional path to save event journal JSON trace")

    # cortex workflow inspect
    wf_inspect = wf_sub.add_parser("inspect", help="Inspect execution graph and lineage for workflow ID or file")
    _ = wf_inspect.add_argument("workflow_id", help="Workflow ID or path to event trace JSON file")

    # cortex workflow replay
    wf_replay = wf_sub.add_parser("replay", help="Deterministically replay workflow execution trace")
    _ = wf_replay.add_argument("workflow_id", help="Workflow ID or path to event trace JSON file")

    args = parser.parse_args(argv)
    cmd = str(getattr(args, "command", ""))
    wf_cmd = str(getattr(args, "wf_command", ""))
    json_mode = bool(getattr(args, "json", False))

    try:
        if cmd == "init":
            p_name = str(getattr(args, "project_name", "my_cortex_app"))
            p_type = str(getattr(args, "type", "app"))
            path = scaffold_project(p_name, project_type=p_type)
            if json_mode:
                print(json.dumps({"status": "success", "command": "init", "project": p_name, "path": path}))
            else:
                print(f"[+] Successfully scaffolded Cortex {p_type} project at: {path}")
            return 0

        elif cmd == "workflow":
            if wf_cmd == "run":
                wf_file = str(getattr(args, "workflow_file", ""))
                out_file = cast(str | None, getattr(args, "output", None))
                res = run_workflow_file(wf_file, output_file=out_file)
                if json_mode:
                    print(json.dumps({"status": "success", "command": "workflow run", "result": res}))
                else:
                    print("[+] Workflow execution finished.")
                    print(f"    ID:          {res['workflow_id']}")
                    print(f"    State:       {res['state']}")
                    print(f"    Events Log:  {res['event_count']}")
                    print(f"    Trace Saved: {res['output_file']}")
                return 0

            elif wf_cmd == "inspect":
                wf_id = str(getattr(args, "workflow_id", ""))
                res = inspect_workflow(wf_id)
                if json_mode:
                    print(json.dumps({"status": "success", "command": "workflow inspect", "result": res}))
                else:
                    causality_tree = cast(list[str], res.get("causality_tree", []))
                    failed_nodes = cast(list[dict[str, object]], res.get("failed_nodes", []))

                    print("=== Cortex Execution Graph Inspection ===")
                    print(f"Workflow ID:   {res['workflow_id']}")
                    print(f"Name:          {res['name']}")
                    print(f"Goal:          {res['goal']}")
                    print(f"State:         {res['state']}")
                    print(f"Total Nodes:   {res['node_count']}")
                    print("\n--- Causality Tree ---")
                    for line in causality_tree:
                        print(f"  {line}")
                    if failed_nodes:
                        print(f"\n[!] Verification Failures ({len(failed_nodes)}):")
                        for node in failed_nodes:
                            print(f"    - Node {node['id']}: {node['payload']}")
                    else:
                        print("\n[+] Verification Status: ALL PASSED")
                return 0

            elif wf_cmd == "replay":
                wf_id = str(getattr(args, "workflow_id", ""))
                res = replay_workflow(wf_id)
                is_deterministic = bool(res.get("deterministic", False))
                if json_mode:
                    print(
                        json.dumps(
                            {
                                "status": "success" if is_deterministic else "error",
                                "command": "workflow replay",
                                "result": res,
                            }
                        )
                    )
                else:
                    print("=== Cortex Deterministic Replay Engine ===")
                    print(f"Workflow ID:      {res['workflow_id']}")
                    print(f"Events Replayed:  {res['events_replayed']}")
                    print(f"Status:           {'SUCCESS' if is_deterministic else 'FAILED'}")
                    print(f"Result:           {res['verification_result']}")

                if not is_deterministic:
                    if not json_mode:
                        _ = _handle_cli_error(
                            WorkflowExecutionError(f"Replay divergence detected for workflow trace: {wf_id}"),
                            json_mode=False,
                        )
                    return 1
                return 0

            else:
                wf_parser.print_help(sys.stderr if not json_mode else sys.stdout)
                return _handle_cli_error(
                    WorkflowExecutionError("Missing or invalid workflow subcommand"), json_mode=json_mode
                )

        else:
            parser.print_help(sys.stderr if not json_mode else sys.stdout)
            return _handle_cli_error(WorkflowExecutionError("Missing or invalid command"), json_mode=json_mode)

    except Exception as err:
        return _handle_cli_error(err, json_mode=json_mode)


if __name__ == "__main__":
    sys.exit(main())
