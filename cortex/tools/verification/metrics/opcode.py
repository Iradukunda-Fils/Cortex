"""
Instruction Opcode Coverage Metric Tracker
"""

from typing import Any

from cortex.tools.verification.metrics.base import BaseMetric
from cortex.tools.verification.schema import CanonicalState


class OpcodeMetric(BaseMetric):
    def __init__(self):
        self.seen_opcodes: set[str] = set()
        self.total_opcodes = 18

    def record_step(self, step: CanonicalState):
        self.seen_opcodes.add(step.instruction)

    def get_summary(self) -> dict[str, Any]:
        count = len(self.seen_opcodes)
        pct = min(100.0, (count / float(self.total_opcodes)) * 100.0)
        return {"unique_opcodes_seen": count, "coverage_percentage": round(pct, 1)}
