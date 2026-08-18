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


class TestCLIDiagnosticOutputFormatting(unittest.TestCase):
    """Validate CLI human diagnostic blocks and machine JSON stream separation."""

    def test_missing_workflow_file_human_error_format(self) -> None:
        """Missing workflow file outputs formatted diagnostic block to stderr with exit code 1."""
        import io
        import sys

        stderr_buf = io.StringIO()
        old_stderr = sys.stderr
        try:
            sys.stderr = stderr_buf
            exit_code = main(["workflow", "run", "/nonexistent/path/wf.json"])
        finally:
            sys.stderr = old_stderr

        self.assertEqual(exit_code, 1)
        err_output = stderr_buf.getvalue()
        self.assertIn("CORTEX CLI DIAGNOSTIC ERROR REPORT", err_output)
        self.assertIn("WORKFLOW_FAILED (Exit Code 1)", err_output)

    def test_missing_workflow_file_json_error_format(self) -> None:
        """Missing workflow file with --json outputs valid JSON to stderr with exit code 1."""
        import io
        import sys

        stderr_buf = io.StringIO()
        old_stderr = sys.stderr
        try:
            sys.stderr = stderr_buf
            exit_code = main(["--json", "workflow", "run", "/nonexistent/path/wf.json"])
        finally:
            sys.stderr = old_stderr

        self.assertEqual(exit_code, 1)
        err_output = stderr_buf.getvalue()
        payload = json.loads(err_output)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error_code"], "WORKFLOW_FAILED")
        self.assertEqual(payload["exit_code"], 1)
        self.assertIn("remediation", payload)

    def test_successful_init_json_format_to_stdout(self) -> None:
        """Successful init --json outputs success payload to stdout with exit code 0."""
        import io
        import sys

        test_dir = tempfile.mkdtemp(prefix="cortex_cli_json_test_")
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        try:
            sys.stdout, sys.stderr = stdout_buf, stderr_buf
            target = os.path.join(test_dir, "json_app")
            exit_code = main(["--json", "init", target])
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buf.getvalue(), "")
        payload = json.loads(stdout_buf.getvalue())
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["command"], "init")


if __name__ == "__main__":
    _ = unittest.main()
