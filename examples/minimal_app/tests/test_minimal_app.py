"""
Test suite for 01_minimal_app.
"""

import unittest

from examples.minimal_app.main import run_pipeline
from examples.minimal_app.tasks import process_text


class TestMinimalApp(unittest.TestCase):
    def test_task_execution(self) -> None:
        """Verifies Level 1 task execution and default specification properties."""
        res_text = process_text("hello world")
        self.assertEqual(res_text, "HELLO WORLD")

        # Level 1 tasks default to 1000m CPU and 512MiB RAM
        self.assertTrue(hasattr(process_text, "spec"))
        self.assertEqual(process_text.spec.cpu_mcores, 1000)
        self.assertEqual(process_text.spec.memory_bytes, 512 * 1024 * 1024)

    def test_pipeline_execution(self) -> None:
        """Verifies overall application pipeline returns expected structure."""
        out = run_pipeline()
        self.assertEqual(out["header"], "HELLO CORTEX DEVELOPER PLATFORM")
        self.assertEqual(out["summary"]["count"], 3)


if __name__ == "__main__":
    unittest.main()
