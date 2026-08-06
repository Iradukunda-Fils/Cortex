"""
Object Registry & Resource Handle Management
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, Set

@dataclass(frozen=True)
class Capability:
    name: str

@dataclass(frozen=True)
class ResourceHandle:
    handle_id: str
    resource_type: str
    capabilities: Set[Capability]

class ObjectRegistry:
    def __init__(self):
        self._actors: Dict[str, Any] = {}
        self._handles: Dict[str, ResourceHandle] = {}

    def register_actor(self, actor_id: str, actor_instance: Any) -> None:
        self._actors[actor_id] = actor_instance

    def get_actor(self, actor_id: str) -> Optional[Any]:
        return self._actors.get(actor_id)

    def register_handle(self, handle: ResourceHandle) -> None:
        self._handles[handle.handle_id] = handle

    def get_handle(self, handle_id: str) -> Optional[ResourceHandle]:
        return self._handles.get(handle_id)
