"""
Plugin Loader & Capability Negotiation Engine

Enforces the security boundary between plugins and the Kernel Core.
Plugins receive only the Resource Handles and Runtime Context scoped
to their declared capabilities — never raw kernel internals.
"""

import enum
from dataclasses import dataclass, field

from cortex.tools.kernel.plugin.manifest import PluginManifest, validate_manifest


class PluginState(str, enum.Enum):
    REGISTERED = "REGISTERED"
    NEGOTIATING = "NEGOTIATING"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


@dataclass
class PluginRegistration:
    """Runtime representation of a loaded plugin."""

    manifest: PluginManifest
    state: PluginState = PluginState.REGISTERED
    granted_capabilities: set[str] = field(default_factory=set)
    denied_capabilities: list[str] = field(default_factory=list)


class CapabilityNegotiator:
    """Evaluates plugin capability requests against the platform's
    available capability set and security policy."""

    platform_capabilities: set[str]

    def __init__(self, platform_capabilities: set[str]):
        self.platform_capabilities = platform_capabilities

    def negotiate(self, manifest: PluginManifest) -> PluginRegistration:
        """Evaluates a plugin manifest and returns a PluginRegistration
        with granted/denied capability sets."""
        validate_manifest(manifest)
        registration = PluginRegistration(manifest=manifest, state=PluginState.NEGOTIATING)

        granted: set[str] = set()
        denied: list[str] = []

        for cap in manifest.required_capabilities:
            if cap in self.platform_capabilities:
                granted.add(cap)
            else:
                denied.append(cap)

        registration.granted_capabilities = granted
        registration.denied_capabilities = denied

        if denied:
            registration.state = PluginState.REJECTED
        else:
            registration.state = PluginState.ACTIVE

        return registration


class PluginRegistry:
    """Manages the lifecycle of all registered plugins."""

    negotiator: CapabilityNegotiator
    _plugins: dict[str, PluginRegistration]

    def __init__(self, platform_capabilities: set[str]):
        self.negotiator = CapabilityNegotiator(platform_capabilities)
        self._plugins = {}

    def register(self, manifest: PluginManifest) -> PluginRegistration:
        """Register a plugin via manifest. Returns the negotiation result."""
        registration = self.negotiator.negotiate(manifest)
        self._plugins[manifest.name] = registration
        return registration

    def get_plugin(self, name: str) -> PluginRegistration | None:
        return self._plugins.get(name)

    def get_active_plugins(self) -> list[PluginRegistration]:
        return [p for p in self._plugins.values() if p.state == PluginState.ACTIVE]

    def get_rejected_plugins(self) -> list[PluginRegistration]:
        return [p for p in self._plugins.values() if p.state == PluginState.REJECTED]
