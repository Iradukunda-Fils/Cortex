"""
Verification Test Suite for 05_advanced_polyglot_app.
"""

import unittest

from examples.advanced_polyglot_app.tasks import (
    analyze_tensor_rms,
    compute_financial_dot_product,
    validate_token,
)
from examples.advanced_polyglot_app.workflows.polyglot_workflow import (
    execute_polyglot_workflow,
)


class TestPolyglotApp(unittest.TestCase):
    def test_rust_checksum_task(self):
        res = validate_token("test-token")
        self.assertIn("rust_checksum", res)
        self.assertGreater(res["rust_checksum"], 0)

    def test_c_dot_product_task(self):
        res = compute_financial_dot_product([1.0, 2.0], [3.0, 4.0])
        self.assertEqual(res, 11.0)

    def test_cpp_rms_task(self):
        res = analyze_tensor_rms([3.0, 4.0])
        self.assertEqual(res, 3.5355339059327378)

    def test_polyglot_workflow_execution(self):
        res = execute_polyglot_workflow("cortex-token-123", [1.0, 2.0, 3.0], [4.0, 5.0, 6.0])
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["c_dot_product"], 32.0)
        self.assertGreater(res["auth"]["rust_checksum"], 0)


if __name__ == "__main__":
    unittest.main()
