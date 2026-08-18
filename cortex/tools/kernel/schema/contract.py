"""
Kernel Service Declarative Contracts
"""

from dataclasses import dataclass

from cortex.tools.kernel.schema.event import Event
from cortex.tools.kernel.schema.message import BaseEvent


@dataclass(frozen=True)
class ServiceContract:
    """Contract advertising event types consumed and produced by a Kernel Service."""

    service_name: str
    consumes: list[type[Event | BaseEvent]]
    produces: list[type[Event | BaseEvent]]
