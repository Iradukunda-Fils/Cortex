"""
Bounded, Priority-Aware Mailbox for Kernel Actors
"""

import heapq
from typing import Any, Tuple

class Mailbox:
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self._queue: list[Tuple[int, int, Any]] = []
        self._counter = 0

    def push(self, message: Any, priority: int = 10) -> bool:
        if len(self._queue) >= self.capacity:
            return False
        self._counter += 1
        heapq.heappush(self._queue, (priority, self._counter, message))
        return True

    def pop(self) -> Any:
        if not self._queue:
            return None
        _, _, message = heapq.heappop(self._queue)
        return message

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def size(self) -> int:
        return len(self._queue)
