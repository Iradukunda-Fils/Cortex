"""
Public Plugin Interface & Capability Management for Cortex Platform
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

from cortex.schema.events import BaseEvent
from cortex.tools.kernel.plugin.manifest import PluginManifest


@dataclass(frozen=True)
class Capability:
    """Public capability representation for permission grants."""
    name: str


@dataclass
class PluginContext:
    """Runtime context provided to plugins, scoped strictly to granted capabilities."""
    session_id: str
    granted_capabilities: set[str] | frozenset[str]
    publish_func: Callable[[BaseEvent], None]

    def __post_init__(self) -> None:
        object.__setattr__(self, "granted_capabilities", frozenset(self.granted_capabilities))

    def publish(self, event: BaseEvent) -> None:
        """Publish an event to the runtime event bus."""
        self.publish_func(event)

    def has_capability(self, cap_name: str) -> bool:
        """Check if a capability was granted to this plugin instance."""
        return cap_name in self.granted_capabilities


class BasePlugin(ABC):
    """Abstract Base Class for all external Cortex plugins."""
    manifest: PluginManifest
    context: PluginContext | None

    def __init__(self, manifest: PluginManifest):
        self.manifest = manifest
        self.context = None

    def set_context(self, context: PluginContext) -> None:
        """Attach runtime context after capability negotiation."""
        self.context = context

    @abstractmethod
    def on_event(self, event: BaseEvent) -> None:
        """Handle incoming events matching the plugin's consumed event contracts."""
