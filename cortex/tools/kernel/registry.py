"""
Object Registry & Resource Handle Management
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Capability:
    name: str

@dataclass(frozen=True)
class ResourceHandle:
    handle_id: str
    resource_type: str
    capabilities: set[Capability]

class ObjectRegistry:
    _actors: dict[str, object]
    _handles: dict[str, ResourceHandle]

    def __init__(self):
        self._actors = {}
        self._handles = {}

    def register_actor(self, actor_id: str, actor_instance: object) -> None:
        self._actors[actor_id] = actor_instance

    def get_actor(self, actor_id: str) -> object | None:
        return self._actors.get(actor_id)

    def register_handle(self, handle: ResourceHandle) -> None:
        self._handles[handle.handle_id] = handle

    def get_handle(self, handle_id: str) -> ResourceHandle | None:
        return self._handles.get(handle_id)
