"""
Invariant Safety Verification Suite

Tests Epoch Monotonicity, Neutral Trap Semantics, and Single Retirement Policy.
"""

import unittest
from typing import cast, override
from cortex.tools.verification.invariants.capability import (
    EpochMonotonicityInvariant,
    NeutralTrapInvariant,
    SingleRetirementInvariant,
)
from cortex.tools.verification.schema.event import CommitEventV1, PureArchitecturalStateV1, ObservationMetadataV1


class TestInvariantSafety(unittest.TestCase):
    monotonicity: EpochMonotonicityInvariant = cast(EpochMonotonicityInvariant, cast(object, None))
    neutral_trap: NeutralTrapInvariant = cast(NeutralTrapInvariant, cast(object, None))
    single_retirement: SingleRetirementInvariant = cast(SingleRetirementInvariant, cast(object, None))

    @override
    def setUp(self):
        self.monotonicity = EpochMonotonicityInvariant()
        self.neutral_trap = NeutralTrapInvariant()
        self.single_retirement = SingleRetirementInvariant()

    def _create_event(
        self,
        step: int = 1,
        epoch: int = 0,
        trap_triggered: bool = False,
        trap_val: int = 0,
        reg_writes: dict[str, str] | None = None,
    ) -> CommitEventV1:
        return CommitEventV1(
            schema_version=1,
            architectural=PureArchitecturalStateV1(
                pc="0x00001000",
                instruction="0x00000000",
                privilege_mode="Machine",
                registers=reg_writes or {},
                stcr=[{"id": 0, "valid": True, "epoch": epoch}],
                trap={"triggered": trap_triggered, "trap_val": trap_val},
            ),
            observation=ObservationMetadataV1(
                step=step,
                cycle=step,
                timestamp_ns=0,
                target_name="verification_test",
                commit_id="dfa2d43",
                adapter_version="1.0.0",
            ),
        )

    def test_epoch_monotonicity_invariant(self):
        """Epoch must remain in valid 16-bit range (0 to 65535)."""
        valid_event = self._create_event(epoch=5)
        res_pass = self.monotonicity.check(valid_event)
        self.assertTrue(res_pass.passed)

        invalid_event = self._create_event(epoch=70000)
        res_fail = self.monotonicity.check(invalid_event)
        self.assertFalse(res_fail.passed)

    def test_neutral_trap_semantics_invariant(self):
        """Neutral traps require trap_val == 0."""
        valid_trap = self._create_event(trap_triggered=True, trap_val=0)
        res_pass = self.neutral_trap.check(valid_trap)
        self.assertTrue(res_pass.passed)

        invalid_trap = self._create_event(trap_triggered=True, trap_val=42)
        res_fail = self.neutral_trap.check(invalid_trap)
        self.assertFalse(res_fail.passed)

    def test_single_retirement_policy_invariant(self):
        """Step count must be greater than or equal to 1."""
        valid_step = self._create_event(step=1)
        res_pass = self.single_retirement.check(valid_step)
        self.assertTrue(res_pass.passed)

        invalid_step = self._create_event(step=0)
        res_fail = self.single_retirement.check(invalid_step)
        self.assertFalse(res_fail.passed)


if __name__ == "__main__":
    _ = unittest.main()
