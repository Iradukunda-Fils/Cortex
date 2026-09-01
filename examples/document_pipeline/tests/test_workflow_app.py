"""
Test suite for 03_workflow_app document pipeline workflow.
"""

import unittest

from examples.document_pipeline.tasks import export_summary, extract_entities, fetch_document
from examples.document_pipeline.workflows import execute_document_pipeline


class TestWorkflowApp(unittest.TestCase):
    def test_individual_tasks(self) -> None:
        """Verifies individual document pipeline task behavior."""
        raw = fetch_document("DOC-100")
        self.assertEqual(raw["doc_id"], "DOC-100")

        analysis = extract_entities(raw)
        self.assertEqual(analysis["doc_id"], "DOC-100")
        self.assertGreater(analysis["word_count"], 0)

        exp = export_summary(analysis)
        self.assertEqual(exp["export_id"], "EXP-DOC-100")
        self.assertEqual(exp["status"], "COMPLETED")

    def test_workflow_orchestration(self) -> None:
        """Verifies end-to-end workflow execution state and output."""
        res = execute_document_pipeline("DOC-200")
        self.assertEqual(res["state"], "COMPLETED")
        self.assertEqual(res["export"]["export_id"], "EXP-DOC-200")


if __name__ == "__main__":
    unittest.main()
