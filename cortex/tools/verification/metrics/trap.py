"""
Trap Cause Path Coverage Metric Tracker
"""

from typing import Any

from cortex.tools.verification.metrics.base import BaseMetric
from cortex.tools.verification.schema import CanonicalState


class TrapMetric(BaseMetric):
    def __init__(self):
        self.seen_trap_codes: set[int] = set()
        self.total_trap_codes = 5

    def record_step(self, step: CanonicalState):
        if step.trap.triggered:
            self.seen_trap_codes.add(step.trap.cause_code)

    def get_summary(self) -> dict[str, Any]:
        count = len(self.seen_trap_codes)
        pct = min(100.0, (count / float(self.total_trap_codes)) * 100.0)
        return {
            "trap_cause_codes_seen": sorted(list(self.seen_trap_codes)),
            "coverage_percentage": round(pct, 1)
        }
