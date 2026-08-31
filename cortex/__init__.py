"""
Cortex Platform Public API Package

Provides vendor-neutral, technology-neutral semantic execution layer,
workflow boundary management, sandboxed capability negotiation, and verification.
"""

from cortex.client import CortexClient
from cortex.compat import override
from cortex.exceptions import (
    CapabilityViolationError,
    CortexError,
    ManifestError,
    WorkflowExecutionError,
)
from cortex.plugin import BasePlugin, Capability, PluginContext, PluginManifest
from cortex.schema import (
    BaseEvent,
    CommandIssuedEvent,
    DriverTelemetryEvent,
    IntentEvent,
    PlanGeneratedEvent,
    TelemetryEvent,
    VerificationResultEvent,
    Workflow,
    WorkflowPolicy,
    WorkflowState,
)
from cortex.task import TaskSpecification, task
from cortex.tools.kernel.services.event_store import EventStoreService as EventStore

__all__ = [
    "BaseEvent",
    "BasePlugin",
    "Capability",
    "CapabilityViolationError",
    "CommandIssuedEvent",
    "CortexClient",
    "CortexError",
    "DriverTelemetryEvent",
    "EventStore",
    "IntentEvent",
    "ManifestError",
    "PlanGeneratedEvent",
    "PluginContext",
    "PluginManifest",
    "TaskSpecification",
    "TelemetryEvent",
    "VerificationResultEvent",
    "Workflow",
    "WorkflowExecutionError",
    "WorkflowPolicy",
    "WorkflowState",
    "override",
    "task",
]

