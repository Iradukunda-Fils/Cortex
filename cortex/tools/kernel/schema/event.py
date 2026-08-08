"""
Domain Event Hierarchy for Cortex Kernel Runtime
"""

from dataclasses import dataclass, field
from typing import Optional, Dict
import time
import uuid

@dataclass(frozen=True)
class Event:
    """Universal Base Envelope for Kernel Runtime IPC Events."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_event_id: Optional[str] = None
    root_event_id: Optional[str] = None
    causation_id: Optional[str] = None
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    sequence_number: int = 0
    timestamp_ns: int = field(default_factory=lambda: time.time_ns())

@dataclass(frozen=True)
class VerificationEvent(Event):
    """Event category for hardware, formal, and simulation correctness."""
    pass

@dataclass(frozen=True)
class RawRTLTraceEvent(VerificationEvent):
    """Raw telemetry frame emitted by hardware drivers or Verilator simulators."""
    pc: int = 0
    raw_instruction: str = ""
    eff_trap: bool = False
    trap_cause: int = 0
    stcr_registers: Dict[int, str] = field(default_factory=dict)

@dataclass(frozen=True)
class CommitVerifiedEvent(VerificationEvent):
    """Domain decision event emitted after formal oracle state verification."""
    step: int = 0
    verified: bool = True
    failing_field: Optional[str] = None

@dataclass(frozen=True)
class MotorFeedbackEvent(Event):
    """Driver raw telemetry event for physical or mock actuators."""
    actuator_id: str = ""
    position: float = 0.0
    velocity: float = 0.0

@dataclass(frozen=True)
class InferenceCompletedEvent(Event):
    """LLM agent or inference engine response event."""
    agent_id: str = ""
    prompt_tokens: int = 0
    completion: str = ""
