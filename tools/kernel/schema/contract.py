"""
Kernel Service Declarative Contracts
"""

from dataclasses import dataclass
from typing import List, Type
from tools.kernel.schema.event import Event

@dataclass(frozen=True)
class ServiceContract:
    """Contract advertising event types consumed and produced by a Kernel Service."""
    service_name: str
    consumes: List[Type[Event]]
    produces: List[Type[Event]]
