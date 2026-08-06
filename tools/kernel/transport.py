"""
Transport Layer Abstractions & InMemoryTransport Implementation
"""

from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Type
from tools.kernel.schema.event import Event

EventHandler = Callable[[Event], None]

class EventPublisher(ABC):
    @abstractmethod
    def publish(self, event: Event) -> None:
        pass

class EventSubscriber(ABC):
    @abstractmethod
    def subscribe(self, event_type: Type[Event], handler: EventHandler) -> None:
        pass

class InMemoryTransport(EventPublisher, EventSubscriber):
    def __init__(self):
        self._handlers: Dict[Type[Event], List[EventHandler]] = {}
        self._history: List[Event] = []

    def subscribe(self, event_type: Type[Event], handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def publish(self, event: Event) -> None:
        self._history.append(event)
        # Notify subscribers of exact type or wildcard Event base class
        for event_cls, handlers in self._handlers.items():
            if issubclass(type(event), event_cls):
                for handler in handlers:
                    handler(event)

    def get_history(self) -> List[Event]:
        return list(self._history)
