"""
Unified Control & Execution Message Hierarchy for Cortex Kernel Runtime
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import time
import uuid

@dataclass(frozen=True)
class Intent:
    """Represents WHAT is desired (Goal / Action Request)."""
    intent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    goal: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp_ns: int = field(default_factory=lambda: time.time_ns())

@dataclass(frozen=True)
class Plan:
    """Represents HOW the Intent is decomposed into structured steps."""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    intent_id: str = ""
    correlation_id: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    timestamp_ns: int = field(default_factory=lambda: time.time_ns())

@dataclass(frozen=True)
class Command:
    """Represents EXECUTE THIS SINGLE OPERATION."""
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str = ""
    correlation_id: str = ""
    action: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp_ns: int = field(default_factory=lambda: time.time_ns())

@dataclass(frozen=True)
class Event:
    """Represents SOMETHING THAT ALREADY HAPPENED (Immutable Fact)."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    causation_id: Optional[str] = None
    correlation_id: str = ""
    root_id: str = ""
    timestamp_ns: int = field(default_factory=lambda: time.time_ns())

@dataclass(frozen=True)
class DriverTelemetryEvent(Event):
    """Raw execution feedback from hardware, tools, or RTL models."""
    status: str = "ok"
    payload: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class VerificationResultEvent(Event):
    """Verification/Invariant evaluation result derived from Telemetry."""
    passed: bool = True
    rule_id: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
