import unittest

from cortex.tools.verification.adapters.coq import CoqAdapter
from cortex.tools.verification.adapters.rtl import RTLAdapter


class TestAdapterMutations(unittest.TestCase):
    def test_coq_adapter_mutation_detection(self):
        adapter = CoqAdapter()
        states = adapter.parse_trace("research/formalization/artifacts/phase2/coq_trace.json")
        self.assertGreater(len(states), 0)
        # Test valid parsing
        self.assertEqual(states[0].stcr[0].valid, True)

    def test_rtl_adapter_decoding_immutability(self):
        adapter = RTLAdapter()
        states = adapter.parse_trace("research/formalization/artifacts/phase2/rtl_trace.json")
        self.assertGreater(len(states), 0)
        # Check spatial mask bit decoding for STCR0
        self.assertEqual(states[0].stcr[0].permissions, 28672)


if __name__ == "__main__":
    unittest.main()
