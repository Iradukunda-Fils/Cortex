"""
Test suite for 04_plugin_app standard Python plugin architecture.
"""

import unittest

from examples.plugin_app.main import run_plugin_pipeline
from examples.plugin_app.plugins.analysis.tasks import analyze_payload
from examples.plugin_app.plugins.ingestion.tasks import read_payload


class TestPluginApp(unittest.TestCase):
    def test_pure_python_plugin_tasks(self) -> None:
        """Verifies pure Python plugin tasks run without requiring binding.py or C FFI."""
        payload = read_payload("SRC-TEST")
        self.assertEqual(payload["source_id"], "SRC-TEST")

        analysis = analyze_payload(payload)
        self.assertEqual(analysis["metrics"]["word_count"], 5)

    def test_plugin_pipeline_registration(self) -> None:
        """Verifies plugin registration and manifest capabilities with CortexClient."""
        res = run_plugin_pipeline()
        self.assertEqual(res["source"], "SRC-9901")
        self.assertIn("ingestion", res["plugins_registered"])
        self.assertIn("analysis", res["plugins_registered"])


if __name__ == "__main__":
    unittest.main()
