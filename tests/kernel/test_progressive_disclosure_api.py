"""
Unit Test Suite for Cortex Progressive Disclosure Developer API
Tests Level 1 (@cortex.task), Level 2 (@cortex.task(resources=...)), and physical hardware discovery.
"""

import unittest

import cortex
from cortex.tools.kernel.resource_authority import discover_physical_capacity, parse_resource_unit


class TestProgressiveDisclosureAPI(unittest.TestCase):
    def test_physical_capacity_discovery(self):
        """Validates physical hardware capacity discovery on host machine."""
        cpu_mcores, memory_bytes = discover_physical_capacity()
        self.assertGreater(cpu_mcores, 0, "Discovered CPU millicores must be > 0")
        self.assertGreater(memory_bytes, 0, "Discovered memory bytes must be > 0")

    def test_unit_normalization(self):
        """Validates unit parsing for human-friendly strings."""
        self.assertEqual(parse_resource_unit("4GiB", default_unit="memory"), 4 * 1024 * 1024 * 1024)
        self.assertEqual(parse_resource_unit("512MiB", default_unit="memory"), 512 * 1024 * 1024)
        self.assertEqual(parse_resource_unit("2500m", default_unit="cpu"), 2500)
        self.assertEqual(parse_resource_unit("2", default_unit="cpu"), 2000)
        self.assertEqual(parse_resource_unit("100Mbps", default_unit="network"), 100)

    def test_level_1_simple_task_decorator(self):
        """Validates Level 1 @cortex.task simple decoration."""

        @cortex.task
        def add(a: int, b: int) -> int:
            return a + b

        result = add(3, 5)
        self.assertEqual(result, 8)
        self.assertTrue(hasattr(add, "spec"))
        self.assertEqual(add.spec.cpu_mcores, 1000)  # Default 1 CPU core

    def test_level_2_resource_aware_task_decorator(self):
        """Validates Level 2 @cortex.task(resources=...) decoration."""

        @cortex.task(resources={"cpu": "4", "memory": "8GiB", "gpu": 1})
        def process_data(batch_id: str) -> str:
            return f"Processed {batch_id}"

        res = process_data("B-101")
        self.assertEqual(res, "Processed B-101")
        self.assertTrue(hasattr(process_data, "spec"))
        self.assertEqual(process_data.spec.cpu_mcores, 4000)
        self.assertEqual(process_data.spec.memory_bytes, 8 * 1024 * 1024 * 1024)
        self.assertEqual(process_data.spec.gpu_count, 1)


if __name__ == "__main__":
    unittest.main()
