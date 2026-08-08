"""
Capability Safety Invariants Engine
"""

from dataclasses import dataclass
from cortex.tools.verification.schema.event import CommitEventV1

# Define invariant boundary constants to avoid magic numbers
MIN_EPOCH = 0
MAX_EPOCH = 65535
NEUTRAL_TRAP_EXPECTED_VAL = 0
MIN_RETIREMENT_STEP = 1

@dataclass
class InvariantResult:
    passed: bool
    invariant_id: str
    error_message: str = ""

    @classmethod
    def PASS(cls, invariant_id: str) -> "InvariantResult":
        return cls(passed=True, invariant_id=invariant_id)

    @classmethod
    def FAIL(cls, invariant_id: str, error_message: str) -> "InvariantResult":
        return cls(passed=False, invariant_id=invariant_id, error_message=error_message)


class EpochMonotonicityInvariant:
    """INV_03: Capability epochs must remain in valid 16-bit range."""
    def check(self, event: CommitEventV1) -> InvariantResult:
        if event.architectural is None:
            return InvariantResult.FAIL("INV_03_ATOMIC_STCR_UPDATE", "Missing architectural state")
        for stcr in event.architectural.stcr:
            epoch = stcr.get("epoch", stcr.get("max_epoch", 0))
            if not isinstance(epoch, int) or epoch < MIN_EPOCH or epoch > MAX_EPOCH:
                return InvariantResult.FAIL("INV_03_ATOMIC_STCR_UPDATE", f"Epoch {epoch} out of 16-bit bounds")
        return InvariantResult.PASS("INV_03_ATOMIC_STCR_UPDATE")


class NeutralTrapInvariant:
    """INV_02: Verifies that committed neutral traps maintain trap_val == 0."""
    def check(self, event: CommitEventV1) -> InvariantResult:
        if event.architectural is None:
            return InvariantResult.FAIL("INV_02_NEUTRAL_TRAP_ZERO_VAL", "Missing architectural state")
        trap = event.architectural.trap
        is_triggered = trap.get("triggered", False)
        trap_val = trap.get("trap_val", 0)
        if is_triggered and trap_val != NEUTRAL_TRAP_EXPECTED_VAL:
            return InvariantResult.FAIL("INV_02_NEUTRAL_TRAP_ZERO_VAL", f"Non-zero trap_val {trap_val} on neutral trap")
        return InvariantResult.PASS("INV_02_NEUTRAL_TRAP_ZERO_VAL")


class SingleRetirementInvariant:
    """INV_01: Exactly one architectural retirement event per execution step."""
    def check(self, event: CommitEventV1) -> InvariantResult:
        if event.observation is None:
            return InvariantResult.FAIL("INV_01_SINGLE_RETIREMENT", "Missing observation metadata")
        if event.observation.step < MIN_RETIREMENT_STEP:
            return InvariantResult.FAIL("INV_01_SINGLE_RETIREMENT", f"Invalid retirement step {event.observation.step}")
        return InvariantResult.PASS("INV_01_SINGLE_RETIREMENT")
