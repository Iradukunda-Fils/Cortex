"""
Unified Control & Execution Message Hierarchy for Cortex Kernel Runtime

Domain-Agnostic Event Taxonomy:
    BaseEvent (universal envelope with workflow_id tracing)
    ├── IntentEvent          (User/System goal request)
    ├── PlanGeneratedEvent   (Agent planner output)
    ├── CommandIssuedEvent   (Executor dispatch)
    ├── DriverTelemetryEvent (Hardware/Simulator feedback)
    ├── VerificationResultEvent (Contract assertion result)
    └── CommitEventV1        (Verification Substrate only — domain-isolated)
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import time
import uuid


# ---------------------------------------------------------------------------
# Base Envelope
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BaseEvent:
    """Universal event envelope carrying identity, workflow correlation,
    and causal lineage metadata."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: Optional[str] = None
    causation_id: Optional[str] = None
    correlation_id: str = ""
    root_id: str = ""
    timestamp_ns: int = field(default_factory=lambda: time.time_ns())
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Universal Kernel & Domain Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntentEvent(BaseEvent):
    """Represents WHAT is desired (Goal / Action Request)."""
    intent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    goal: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanGeneratedEvent(BaseEvent):
    """Represents HOW the Intent is decomposed into structured steps."""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    intent_id: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class CommandIssuedEvent(BaseEvent):
    """Represents EXECUTE THIS SINGLE OPERATION."""
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str = ""
    action: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DriverTelemetryEvent(BaseEvent):
    """Raw execution feedback from hardware, tools, or RTL models."""
    driver_id: str = ""
    status: str = "ok"
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VerificationResultEvent(BaseEvent):
    """Verification/Invariant evaluation result derived from Telemetry."""
    passed: bool = True
    rule_id: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Domain-Specific: Verification Substrate (Isolated to Verification Domain)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CommitEventV1(BaseEvent):
    """Immutable architectural commit event scoped exclusively to the
    formal verification service pipeline (Coq / Rust / RTL oracles)."""
    cycle: int = 0
    pc: int = 0
    instruction: int = 0
    register_writes: Dict[str, int] = field(default_factory=dict)
    memory_writes: Dict[str, Any] = field(default_factory=dict)
    exception_code: Optional[int] = None



