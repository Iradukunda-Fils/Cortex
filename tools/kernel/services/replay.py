"""
Deterministic Replay Subsystem for Kernel Event Streams
"""

from typing import List, Dict, Any
from tools.kernel.transport import InMemoryTransport, EventPublisher
from tools.kernel.schema.message import Event

class DeterministicReplayEngine:
    """Executes deterministic replay of recorded event journals."""

    def __init__(self, publisher: EventPublisher):
        self.publisher = publisher

    def replay_journal(self, journal: List[Event]) -> int:
        """Replays an ordered event journal onto the target transport."""
        replayed_count = 0
        for event in journal:
            self.publisher.publish(event)
            replayed_count += 1
        return replayed_count

    @staticmethod
    def verify_replayed_lineage(original: List[Event], replayed: List[Event]) -> Dict[str, Any]:
        """Validates 1:1 causal ID and event sequence immutability."""
        if len(original) != len(replayed):
            return {
                "match": False,
                "reason": f"Length mismatch: original={len(original)}, replayed={len(replayed)}"
            }

        for idx, (orig, repl) in enumerate(zip(original, replayed)):
            if orig.event_id != repl.event_id:
                return {
                    "match": False,
                    "reason": f"Event ID mismatch at index {idx}: {orig.event_id} != {repl.event_id}"
                }
            if orig.causation_id != repl.causation_id:
                return {
                    "match": False,
                    "reason": f"Causation ID mismatch at index {idx}: {orig.causation_id} != {repl.causation_id}"
                }

        return {"match": True, "reason": "100% Deterministic Lineage Preservation Confirmed"}
