"""
Test suite for 02_resource_aware_app.
"""

import unittest

from examples.resource_aware_app.main import run_pipeline
from examples.resource_aware_app.tasks import (
    compute_heavy_aggregations,
    run_model_inference,
)


class TestResourceAwareApp(unittest.TestCase):
    def test_resource_spec_normalization(self) -> None:
        """Verifies resource specification parsing and unit normalization."""
        # compute_heavy_aggregations: cpu="2" (2000m), memory="4GiB" (4398046511 bytes)
        spec1 = compute_heavy_aggregations.spec
        self.assertEqual(spec1.cpu_mcores, 2000)
        self.assertEqual(spec1.memory_bytes, 4 * 1024 * 1024 * 1024)

        # run_model_inference: cpu="4", memory="8GiB", gpu=1, vram="8GiB"
        spec2 = run_model_inference.spec
        self.assertEqual(spec2.cpu_mcores, 4000)
        self.assertEqual(spec2.memory_bytes, 8 * 1024 * 1024 * 1024)
        self.assertEqual(spec2.gpu_count, 1)
        self.assertEqual(spec2.vram_bytes, 8 * 1024 * 1024 * 1024)

    def test_pipeline_execution(self) -> None:
        """Verifies end-to-end execution of resource-aware tasks."""
        res = run_pipeline()
        self.assertEqual(res["aggregations"]["status"], "PROCESSED")
        self.assertEqual(res["inference"]["status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
