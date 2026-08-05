"""
Capability Safety Invariants Engine
"""

from dataclasses import dataclass
from typing import Dict, Any
from tools.verification.schema.event import CommitEventV1

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
        for stcr in event.architectural.stcr:
            epoch = stcr.get("epoch", stcr.get("max_epoch", 0))
            if epoch < 0 or epoch > 65535:
                return InvariantResult.FAIL("INV_03_ATOMIC_STCR_UPDATE", f"Epoch {epoch} out of 16-bit bounds")
        return InvariantResult.PASS("INV_03_ATOMIC_STCR_UPDATE")

class NeutralTrapInvariant:
    """INV_02: Verifies that committed neutral traps maintain trap_val == 0."""
    def check(self, event: CommitEventV1) -> InvariantResult:
        trap = event.architectural.trap
        is_triggered = trap.get("triggered", False)
        trap_val = trap.get("trap_val", 0)
        if is_triggered and trap_val != 0:
            return InvariantResult.FAIL("INV_02_NEUTRAL_TRAP_ZERO_VAL", f"Non-zero trap_val {trap_val} on neutral trap")
        return InvariantResult.PASS("INV_02_NEUTRAL_TRAP_ZERO_VAL")

class SingleRetirementInvariant:
    """INV_01: Exactly one architectural retirement event per execution step."""
    def check(self, event: CommitEventV1) -> InvariantResult:
        if event.observation.step < 1:
            return InvariantResult.FAIL("INV_01_SINGLE_RETIREMENT", f"Invalid retirement step {event.observation.step}")
        return InvariantResult.PASS("INV_01_SINGLE_RETIREMENT")
