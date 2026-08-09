"""
Public Event and Schema Exports for Cortex Platform
"""

from dataclasses import asdict
from typing import cast

from cortex.tools.kernel.schema.message import (
    BaseEvent,
    CommandIssuedEvent,
    DriverTelemetryEvent,
    IntentEvent,
    PlanGeneratedEvent,
    VerificationResultEvent,
)
from cortex.tools.kernel.schema.workflow import Workflow, WorkflowPolicy, WorkflowState

# Public Alias
TelemetryEvent = DriverTelemetryEvent


def event_to_dict(event: BaseEvent) -> dict[str, object]:
    """Serialize BaseEvent subclass to typed JSON-compatible dictionary."""
    d = cast(dict[str, object], asdict(event))
    d["_event_type"] = type(event).__name__
    return d


def dict_to_event(d: dict[str, object]) -> BaseEvent:
    """Deserialize JSON dictionary to corresponding BaseEvent subclass."""
    d_copy = dict(d)
    event_type = str(d_copy.pop("_event_type", "BaseEvent"))

    match event_type:
        case "IntentEvent":
            return IntentEvent(
                workflow_id=cast(str | None, d_copy.get("workflow_id")),
                goal=str(d_copy.get("goal", "")),
                parameters=cast(dict[str, object], d_copy.get("parameters", {})),
                intent_id=str(d_copy.get("intent_id", "")),
                event_id=str(d_copy.get("event_id", "")),
                causation_id=cast(str | None, d_copy.get("causation_id")),
                correlation_id=str(d_copy.get("correlation_id", "")),
                root_id=str(d_copy.get("root_id", "")),
                timestamp_ns=int(str(d_copy.get("timestamp_ns", 0))),
                metadata=cast(dict[str, object], d_copy.get("metadata", {})),
            )
        case "PlanGeneratedEvent":
            return PlanGeneratedEvent(
                workflow_id=cast(str | None, d_copy.get("workflow_id")),
                intent_id=str(d_copy.get("intent_id", "")),
                steps=cast(list[dict[str, object]], d_copy.get("steps", [])),
                plan_id=str(d_copy.get("plan_id", "")),
                event_id=str(d_copy.get("event_id", "")),
                causation_id=cast(str | None, d_copy.get("causation_id")),
                correlation_id=str(d_copy.get("correlation_id", "")),
                root_id=str(d_copy.get("root_id", "")),
                timestamp_ns=int(str(d_copy.get("timestamp_ns", 0))),
                metadata=cast(dict[str, object], d_copy.get("metadata", {})),
            )
        case "CommandIssuedEvent":
            return CommandIssuedEvent(
                workflow_id=cast(str | None, d_copy.get("workflow_id")),
                plan_id=str(d_copy.get("plan_id", "")),
                action=str(d_copy.get("action", "")),
                parameters=cast(dict[str, object], d_copy.get("parameters", {})),
                command_id=str(d_copy.get("command_id", "")),
                event_id=str(d_copy.get("event_id", "")),
                causation_id=cast(str | None, d_copy.get("causation_id")),
                correlation_id=str(d_copy.get("correlation_id", "")),
                root_id=str(d_copy.get("root_id", "")),
                timestamp_ns=int(str(d_copy.get("timestamp_ns", 0))),
                metadata=cast(dict[str, object], d_copy.get("metadata", {})),
            )
        case "DriverTelemetryEvent" | "TelemetryEvent":
            return DriverTelemetryEvent(
                workflow_id=cast(str | None, d_copy.get("workflow_id")),
                driver_id=str(d_copy.get("driver_id", "")),
                status=str(d_copy.get("status", "")),
                payload=cast(dict[str, object], d_copy.get("payload", {})),
                event_id=str(d_copy.get("event_id", "")),
                causation_id=cast(str | None, d_copy.get("causation_id")),
                correlation_id=str(d_copy.get("correlation_id", "")),
                root_id=str(d_copy.get("root_id", "")),
                timestamp_ns=int(str(d_copy.get("timestamp_ns", 0))),
                metadata=cast(dict[str, object], d_copy.get("metadata", {})),
            )
        case "VerificationResultEvent":
            return VerificationResultEvent(
                workflow_id=cast(str | None, d_copy.get("workflow_id")),
                passed=bool(d_copy.get("passed", True)),
                rule_id=str(d_copy.get("rule_id", "")),
                details=cast(dict[str, object], d_copy.get("details", {})),
                metrics=cast(dict[str, object], d_copy.get("metrics", {})),
                event_id=str(d_copy.get("event_id", "")),
                causation_id=cast(str | None, d_copy.get("causation_id")),
                correlation_id=str(d_copy.get("correlation_id", "")),
                root_id=str(d_copy.get("root_id", "")),
                timestamp_ns=int(str(d_copy.get("timestamp_ns", 0))),
                metadata=cast(dict[str, object], d_copy.get("metadata", {})),
            )
        case _:
            return BaseEvent(
                workflow_id=cast(str | None, d_copy.get("workflow_id")),
                event_id=str(d_copy.get("event_id", "")),
                causation_id=cast(str | None, d_copy.get("causation_id")),
                correlation_id=str(d_copy.get("correlation_id", "")),
                root_id=str(d_copy.get("root_id", "")),
                timestamp_ns=int(str(d_copy.get("timestamp_ns", 0))),
                metadata=cast(dict[str, object], d_copy.get("metadata", {})),
            )


__all__ = [
    "BaseEvent",
    "CommandIssuedEvent",
    "DriverTelemetryEvent",
    "IntentEvent",
    "PlanGeneratedEvent",
    "TelemetryEvent",
    "VerificationResultEvent",
    "Workflow",
    "WorkflowPolicy",
    "WorkflowState",
    "dict_to_event",
    "event_to_dict",
]
