"""
Cortex Developer CLI Unit & Integration Test Suite
"""

import json
import os
import shutil
import tempfile
import unittest
from typing import cast, override

from cortex.tools.cli.main import main
from cortex.tools.cli.runner import inspect_workflow, replay_workflow, run_workflow_file
from cortex.tools.cli.scaffolder import scaffold_project


class TestCortexCLI(unittest.TestCase):
    test_dir: str = ""

    @override
    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp(prefix="cortex_cli_test_")

    @override
    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_scaffold_app_and_plugin(self) -> None:
        """Scaffolding app or plugin creates required files."""
        app_path = scaffold_project("my_app", project_type="app", target_dir=os.path.join(self.test_dir, "my_app"))
        self.assertTrue(os.path.exists(os.path.join(app_path, "cortex.json")))
        self.assertTrue(os.path.exists(os.path.join(app_path, "manifest.json")))
        self.assertTrue(os.path.exists(os.path.join(app_path, "workflow.json")))
        self.assertTrue(os.path.exists(os.path.join(app_path, "main.py")))

        plugin_path = scaffold_project("my_plugin", project_type="plugin", target_dir=os.path.join(self.test_dir, "my_plugin"))
        self.assertTrue(os.path.exists(os.path.join(plugin_path, "plugin.py")))

    def test_cli_init_main(self) -> None:
        """CLI main dispatcher executes init command."""
        target = os.path.join(self.test_dir, "scaffolded_via_cli")
        exit_code = main(["init", target, "--type", "app"])
        self.assertEqual(exit_code, 0)
        self.assertTrue(os.path.exists(os.path.join(target, "cortex.json")))

    def test_workflow_run_inspect_replay_lifecycle(self) -> None:
        """Complete workflow lifecycle: run, inspect, and replay."""
        wf_file = os.path.join(self.test_dir, "test_wf.json")
        out_trace = os.path.join(self.test_dir, "trace.json")

        wf_spec = {
            "name": "integration_wf",
            "goal": "Test workflow execution",
            "policy": {"timeout_seconds": 60.0},
            "initial_intent": {"goal": "Run test intent"},
        }
        with open(wf_file, "w", encoding="utf-8") as f:
            json.dump(wf_spec, f)

        # 1. Run
        run_res = run_workflow_file(wf_file, output_file=out_trace)
        self.assertEqual(run_res["state"], "COMPLETED")
        self.assertTrue(os.path.exists(out_trace))

        # 2. Inspect
        inspect_res = inspect_workflow(out_trace)
        self.assertEqual(inspect_res["name"], "integration_wf")
        total_events = cast(int, inspect_res["total_events"])
        self.assertGreaterEqual(total_events, 1)

        # 3. Replay
        replay_res = replay_workflow(out_trace)
        self.assertTrue(cast(bool, replay_res["deterministic"]))
        events_replayed = cast(int, replay_res["events_replayed"])
        self.assertEqual(events_replayed, total_events)


if __name__ == "__main__":
    _ = unittest.main()
