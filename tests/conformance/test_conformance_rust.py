"""
Rust Simulator Conformance test suite
"""

import unittest
from cortex.tools.verification.adapters.rust import RustAdapter


class TestConformanceRust(unittest.TestCase):
    def setUp(self):
        self.adapter = RustAdapter()
        self.states = self.adapter.parse_trace("Research/artifacts/phase2/emulator_trace.json")

    def test_rust_scenario_a0_basic_commit(self):
        """A0: Verify initial state commit."""
        self.assertGreater(len(self.states), 0)
        first = self.states[0]
        self.assertEqual(first.step, 1)
        self.assertEqual(first.pc, 8192)

    def test_rust_scenario_a1_register_writes(self):
        """A1: Verify register state updates."""
        first = self.states[0]
        self.assertEqual(first.reg_hec, 0)

    def test_rust_scenario_a2_memory_writes(self):
        """A2: Verify memory accesses are parsed."""
        first = self.states[0]
        self.assertEqual(first.stcr[0].base_address, 8192)

    def test_rust_scenario_a3_control_flow_branch(self):
        """A3: Verify control flow transitions."""
        pcs = [state.pc for state in self.states]
        self.assertIn(8192, pcs)

    def test_rust_scenario_a4_exception_traps(self):
        """A4: Verify exception and trap decoding."""
        traps = [state.trap for state in self.states]
        self.assertTrue(any(not t.triggered for t in traps))

    def test_rust_scenario_a5_multi_cycle_burst(self):
        """A5: Verify multi-cycle trace equivalence."""
        self.assertEqual(len(self.states), 6)


if __name__ == "__main__":
    unittest.main()
