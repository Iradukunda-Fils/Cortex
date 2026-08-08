"""
Typed Append-Only Event Bus for Broadcasting Immutable CommitEventV1 Instances
"""

from typing import List, Callable
from cortex.tools.verification.schema.event import CommitEventV1

SubscriberCallback = Callable[[CommitEventV1], None]

class EventBus:
    def __init__(self):
        self._subscribers: List[SubscriberCallback] = []
        self._history: List[CommitEventV1] = []

    def subscribe(self, callback: SubscriberCallback) -> None:
        self._subscribers.append(callback)

    def publish(self, event: CommitEventV1) -> None:
        self._history.append(event)
        for subscriber in self._subscribers:
            subscriber(event)

    def get_history(self) -> List[CommitEventV1]:
        return list(self._history)

    def clear(self) -> None:
        self._history.clear()
