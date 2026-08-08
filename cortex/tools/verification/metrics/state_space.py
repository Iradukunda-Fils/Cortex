"""
Unique Architectural State Explorer Metric Tracker
"""

import hashlib
import json
from typing import Dict, Any, Set
from cortex.tools.verification.metrics.base import BaseMetric
from cortex.tools.verification.schema import CanonicalState

class StateSpaceMetric(BaseMetric):
    def __init__(self):
        self.visited_states: Set[str] = set()

    def record_step(self, step: CanonicalState):
        state_dict = step.to_dict()
        state_str = json.dumps(state_dict, sort_keys=True).encode("utf-8")
        state_hash = hashlib.sha256(state_str).hexdigest()[:16]
        self.visited_states.add(state_hash)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "unique_states_explored": len(self.visited_states)
        }
