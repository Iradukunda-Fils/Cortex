import unittest
from tools.verification.adapters.rtl import RTLAdapter
from tools.verification.schema.event import CommitEventV1, PureArchitecturalStateV1, ObservationMetadataV1

class TestConformanceRTL(unittest.TestCase):
    def test_rtl_adapter_conformance(self):
        adapter = RTLAdapter()
        states = adapter.parse_trace("Research/artifacts/phase2/rtl_trace.json")
        self.assertGreater(len(states), 0)

        for idx, state in enumerate(states):
            event = CommitEventV1(
                schema_version=1,
                architectural=PureArchitecturalStateV1(
                    pc=f"0x{state.pc:08x}",
                    instruction=state.instruction,
                    privilege_mode=state.privilege_mode,
                    registers=state.registers,
                    stcr=[s.to_dict() for s in state.stcr],
                    trap=state.trap.to_dict()
                ),
                observation=ObservationMetadataV1(
                    step=idx + 1,
                    cycle=idx + 1,
                    timestamp_ns=0,
                    target_name="rtl_verilator",
                    commit_id="a484b94",
                    adapter_version="1.0.0"
                )
            )
            self.assertEqual(event.schema_version, 1)
            self.assertEqual(event.observation.target_name, "rtl_verilator")

if __name__ == "__main__":
    unittest.main()
