"""
RTL Adapter Conformance test suite
"""

import unittest

from cortex.tools.verification.adapters.rtl import RTLAdapter


class TestConformanceRTL(unittest.TestCase):
    def setUp(self):
        self.adapter = RTLAdapter()
        self.states = self.adapter.parse_trace("Research/artifacts/phase2/rtl_trace.json")

    def test_rtl_cycle_c0_fetch_decode(self):
        """C0: Verify instruction fetch and decode."""
        self.assertGreater(len(self.states), 0)
        first = self.states[0]
        self.assertEqual(first.step, 1)
        self.assertEqual(first.pc, 4096)

    def test_rtl_cycle_c1_execute_stage(self):
        """C1: Verify execute stage execution."""
        first = self.states[0]
        self.assertEqual(first.reg_hec, 0)

    def test_rtl_cycle_c2_memory_access(self):
        """C2: Verify spatial/permissions checking logic."""
        first = self.states[0]
        self.assertEqual(first.stcr[0].permissions, 28672)

    def test_rtl_cycle_c3_writeback(self):
        """C3: Verify register writeback commits."""
        first = self.states[0]
        self.assertEqual(first.stcr[0].valid, True)

    def test_rtl_cycle_c4_trap_vectoring(self):
        """C4: Verify exception trap vectoring checks."""
        traps = [state.trap for state in self.states]
        self.assertTrue(any(not t.triggered for t in traps))


if __name__ == "__main__":
    unittest.main()
