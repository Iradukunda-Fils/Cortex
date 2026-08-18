"""
Transport Layer Abstractions & InMemoryTransport Implementation
"""

from abc import ABC, abstractmethod
from collections.abc import Callable

from cortex.compat import override
from cortex.tools.kernel.schema.event import Event
from cortex.tools.kernel.schema.message import BaseEvent

AnyEvent = Event | BaseEvent
EventHandler = Callable[[AnyEvent], None]


class EventPublisher(ABC):
    @abstractmethod
    def publish(self, event: AnyEvent) -> None:
        pass


class EventSubscriber(ABC):
    @abstractmethod
    def subscribe(self, event_type: type[AnyEvent], handler: EventHandler) -> None:
        pass


class InMemoryTransport(EventPublisher, EventSubscriber):
    _handlers: dict[type[AnyEvent], list[EventHandler]]
    _history: list[AnyEvent]

    def __init__(self):
        self._handlers = {}
        self._history = []

    @override
    def subscribe(self, event_type: type[AnyEvent], handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    @override
    def publish(self, event: AnyEvent) -> None:
        self._history.append(event)
        # Notify subscribers of exact type or wildcard Event base class
        for event_cls, handlers in self._handlers.items():
            if issubclass(type(event), event_cls):
                for handler in handlers:
                    handler(event)

    def get_history(self) -> list[AnyEvent]:
        return list(self._history)
