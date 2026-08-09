"""
Autonomous Repository Auditor Dogfood App Test Suite
"""

import unittest

from examples.repo_auditor.main import run_repo_auditor


class TestRepoAuditorDogfoodApp(unittest.TestCase):
    def test_repo_auditor_normal_execution(self) -> None:
        """Auditor app executes cleanly and passes all invariants under normal permissions."""
        exit_code = run_repo_auditor(simulate_violation=False)
        self.assertEqual(exit_code, 0)

    def test_repo_auditor_sandbox_violation(self) -> None:
        """Auditor app catches unauthorized capability write violation and marks workflow FAILED."""
        exit_code = run_repo_auditor(simulate_violation=True)
        self.assertEqual(exit_code, 0)  # run_repo_auditor returns 0 when violation proof succeeds


if __name__ == "__main__":
    unittest.main()
