import os
import subprocess
import unittest


class TestPhase74DistributedReservationTLA(unittest.TestCase):
    """Test suite validating Phase 7.4 Distributed Reservation TLA+ Model and TLC runner."""

    def setUp(self):
        self.tla_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "verification",
            "tla",
        )
        self.tla_file = os.path.join(self.tla_dir, "Phase7DistributedReservation.tla")
        self.cfg_file = os.path.join(self.tla_dir, "Phase7DistributedReservation.cfg")

    def test_tla_spec_and_config_exist(self):
        """Verify Phase 7.4 TLA+ spec and TLC config files exist."""
        self.assertTrue(os.path.exists(self.tla_file), f"Missing {self.tla_file}")
        self.assertTrue(os.path.exists(self.cfg_file), f"Missing {self.cfg_file}")

    def test_tla_spec_contains_core_invariants(self):
        """Verify TLA+ specification contains required Phase 7.4 distributed invariants."""
        with open(self.tla_file, "r") as f:
            content = f.read()

        required_invariants = [
            "CapacityConservation",
            "GPUExclusiveOwnershipSafety",
            "SingleLeaderPerEpochSafety",
            "QuarantineIsolationSafety",
            "TerminalNonResurrectionSafety",
            "Phase7DistributedSafetyInvariant",
        ]
        for inv in required_invariants:
            self.assertIn(inv, content, f"Missing invariant {inv} in TLA+ spec")


if __name__ == "__main__":
    unittest.main()
