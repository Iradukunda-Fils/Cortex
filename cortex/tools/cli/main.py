"""
Cortex Developer CLI Command Entrypoint

Usage:
    cortex init <project_name> [--type {app|plugin}]
    cortex workflow run <workflow_file> [--output <file>]
    cortex workflow inspect <workflow_id_or_file>
    cortex workflow replay <workflow_id_or_file>
"""

import argparse
import sys
from typing import Sequence, cast
from cortex.tools.cli.runner import inspect_workflow, replay_workflow, run_workflow_file
from cortex.tools.cli.scaffolder import scaffold_project


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

    if cmd == "init":
        p_name = str(getattr(args, "project_name", "my_cortex_app"))
        p_type = str(getattr(args, "type", "app"))
        path = scaffold_project(p_name, project_type=p_type)
        print(f"[+] Successfully scaffolded Cortex {p_type} project at: {path}")
        return 0

    elif cmd == "workflow":
        if wf_cmd == "run":
            wf_file = str(getattr(args, "workflow_file", ""))
            out_file = cast(str | None, getattr(args, "output", None))
            res = run_workflow_file(wf_file, output_file=out_file)
            print("[+] Workflow execution finished.")
            print(f"    ID:          {res['workflow_id']}")
            print(f"    State:       {res['state']}")
            print(f"    Events Log:  {res['event_count']}")
            print(f"    Trace Saved: {res['output_file']}")
            return 0

        elif wf_cmd == "inspect":
            wf_id = str(getattr(args, "workflow_id", ""))
            res = inspect_workflow(wf_id)
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
            print("=== Cortex Deterministic Replay Engine ===")
            print(f"Workflow ID:      {res['workflow_id']}")
            print(f"Events Replayed:  {res['events_replayed']}")
            print(f"Status:           {'SUCCESS' if res['deterministic'] else 'FAILED'}")
            print(f"Result:           {res['verification_result']}")
            return 0 if res["deterministic"] else 1

        else:
            wf_parser.print_help()
            return 1

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
