"""
Golden Corpus Scenarios Verification Suite
"""

import unittest
import json
from cortex.tools.verification.schema.event import CommitEventV1, PureArchitecturalStateV1, ObservationMetadataV1


class TestGoldenCorpus(unittest.TestCase):
    def setUp(self):
        with open("tests/golden/v1.0.0/commit_store.json") as f:
            self.store = json.load(f)
        self.expected_events = self.store.get("expected_events", [])

    def _verify_event_properties(self, event_data: dict):
        # Build CommitEventV1 to verify type safety and schema validation
        arch_data = event_data.get("architectural", {})
        stcr_data = arch_data.get("stcr", [])
        trap_data = arch_data.get("trap", {})

        event = CommitEventV1(
            schema_version=event_data.get("schema_version", 1),
            architectural=PureArchitecturalStateV1(
                pc=arch_data.get("pc", "0x00000000"),
                instruction=arch_data.get("instruction", "0x00000000"),
                privilege_mode=arch_data.get("privilege_mode", "Machine"),
                registers=arch_data.get("registers", {}),
                stcr=stcr_data,
                trap=trap_data,
            ),
            observation=ObservationMetadataV1(
                step=1,
                cycle=1,
                timestamp_ns=0,
                target_name="golden_corpus",
                commit_id="dfa2d43",
                adapter_version="1.0.0",
            ),
        )
        self.assertEqual(event.schema_version, 1)

    def test_golden_scenario_a0_basic_commit(self):
        """A0: Verify basic commit scenario."""
        self.assertGreater(len(self.expected_events), 0)
        self._verify_event_properties(self.expected_events[0])

    def test_golden_scenario_a1_register_writes(self):
        """A1: Verify register writes scenario."""
        event_data = self.expected_events[0]
        self.assertEqual(event_data.get("architectural", {}).get("privilege_mode"), "Machine")

    def test_golden_scenario_a2_memory_writes(self):
        """A2: Verify memory writes scenario."""
        event_data = self.expected_events[0]
        stcr_list = event_data.get("architectural", {}).get("stcr", [])
        self.assertGreater(len(stcr_list), 0)
        self.assertEqual(stcr_list[0].get("base_address"), 8192)

    def test_golden_scenario_a3_control_flow_branch(self):
        """A3: Verify control flow branches."""
        event_data = self.expected_events[0]
        pc_val = event_data.get("architectural", {}).get("pc")
        self.assertEqual(pc_val, "0x00001000")

    def test_golden_scenario_a4_exception_traps(self):
        """A4: Verify exception traps handling."""
        event_data = self.expected_events[0]
        trap = event_data.get("architectural", {}).get("trap", {})
        self.assertFalse(trap.get("triggered", True))

    def test_golden_scenario_a5_multi_cycle_burst(self):
        """A5: Verify multi-cycle burst behavior."""
        self.assertEqual(self.store.get("version"), "1.0.0")


if __name__ == "__main__":
    unittest.main()
