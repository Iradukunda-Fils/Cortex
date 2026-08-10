"""
v0.2.0 Regression: CLI Exit Code and Output Contracts

Validates CLI main() exit codes, error handling, and structured output format.
"""

import json
import os
import shutil
import tempfile
import unittest

from cortex.exceptions import (
    CapabilityViolationError,
    CortexError,
    ManifestError,
    WorkflowExecutionError,
)
from cortex.tools.cli.main import main


class TestCLIExitCodes(unittest.TestCase):
    """Validate CLI exit code contracts."""

    test_dir: str = ""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp(prefix="cortex_cli_regression_")

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_init_returns_zero(self) -> None:
        """CLI init command returns exit code 0 on success."""
        target = os.path.join(self.test_dir, "test_app")
        exit_code = main(["init", target, "--type", "app"])
        self.assertEqual(exit_code, 0)

    def test_init_creates_expected_files(self) -> None:
        """CLI init scaffolds cortex.json, manifest.json, workflow.json, main.py."""
        target = os.path.join(self.test_dir, "scaffolded")
        _ = main(["init", target, "--type", "app"])
        expected_files = ["cortex.json", "manifest.json", "workflow.json", "main.py"]
        for fname in expected_files:
            with self.subTest(file=fname):
                self.assertTrue(
                    os.path.exists(os.path.join(target, fname)),
                    f"Missing scaffolded file: {fname}",
                )

    def test_workflow_run_returns_zero(self) -> None:
        """CLI workflow run returns exit code 0 for valid workflow."""
        wf_file = os.path.join(self.test_dir, "valid_wf.json")
        out_file = os.path.join(self.test_dir, "trace.json")
        wf_spec = {
            "name": "cli_regression_wf",
            "goal": "Test CLI run",
            "policy": {"timeout_seconds": 60.0},
            "initial_intent": {"goal": "Run CLI test"},
        }
        with open(wf_file, "w", encoding="utf-8") as f:
            json.dump(wf_spec, f)

        exit_code = main(["workflow", "run", wf_file, "--output", out_file])
        self.assertEqual(exit_code, 0)
        self.assertTrue(os.path.exists(out_file))

    def test_workflow_replay_deterministic_returns_zero(self) -> None:
        """CLI workflow replay of deterministic trace returns exit code 0."""
        wf_file = os.path.join(self.test_dir, "replay_wf.json")
        out_file = os.path.join(self.test_dir, "replay_trace.json")
        wf_spec = {
            "name": "replay_regression_wf",
            "goal": "Test CLI replay",
            "initial_intent": {"goal": "Replay test"},
        }
        with open(wf_file, "w", encoding="utf-8") as f:
            json.dump(wf_spec, f)

        _ = main(["workflow", "run", wf_file, "--output", out_file])
        exit_code = main(["workflow", "replay", out_file])
        self.assertEqual(exit_code, 0)

    def test_unknown_command_returns_one(self) -> None:
        """CLI with no valid command returns exit code 1."""
        exit_code = main([])
        self.assertEqual(exit_code, 1)

    def test_unknown_workflow_subcommand_returns_one(self) -> None:
        """CLI workflow with no subcommand returns exit code 1."""
        exit_code = main(["workflow"])
        self.assertEqual(exit_code, 1)


class TestExceptionExitCodes(unittest.TestCase):
    """Validate exception exit_code contracts — these are public API."""

    def test_cortex_error_exit_code(self) -> None:
        """CortexError base class has exit_code=1."""
        err = CortexError("test")
        self.assertEqual(err.exit_code, 1)
        self.assertEqual(str(err), "test")

    def test_workflow_execution_error_exit_code(self) -> None:
        """WorkflowExecutionError has exit_code=1."""
        err = WorkflowExecutionError("wf failed", workflow_id="wf_001")
        self.assertEqual(err.exit_code, 1)
        self.assertEqual(err.workflow_id, "wf_001")

    def test_capability_violation_error_exit_code(self) -> None:
        """CapabilityViolationError has exit_code=2."""
        err = CapabilityViolationError("denied", capability="nuclear.launch")
        self.assertEqual(err.exit_code, 2)
        self.assertEqual(err.capability, "nuclear.launch")

    def test_manifest_error_exit_code(self) -> None:
        """ManifestError has exit_code=3."""
        err = ManifestError("bad manifest")
        self.assertEqual(err.exit_code, 3)

    def test_all_exceptions_inherit_cortex_error(self) -> None:
        """All custom exceptions must be CortexError subclasses."""
        self.assertIsInstance(WorkflowExecutionError("t"), CortexError)
        self.assertIsInstance(CapabilityViolationError("t"), CortexError)
        self.assertIsInstance(ManifestError("t"), CortexError)


if __name__ == "__main__":
    _ = unittest.main()
