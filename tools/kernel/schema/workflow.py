"""
First-Class Workflow Primitive & Policy Schema
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
import enum
import time
import uuid

class WorkflowState(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"

@dataclass
class WorkflowPolicy:
    timeout_seconds: float = 300.0
    max_retries: int = 3
    abort_on_verification_failure: bool = True

@dataclass
class Workflow:
    """First-class runtime unit of execution encapsulating autonomous lifecycles."""
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "default_workflow"
    goal: str = ""
    state: WorkflowState = WorkflowState.PENDING
    policy: WorkflowPolicy = field(default_factory=WorkflowPolicy)
    root_intent_id: Optional[str] = None
    execution_graph_id: Optional[str] = None
    created_at_ns: int = field(default_factory=lambda: time.time_ns())
    metadata: Dict[str, Any] = field(default_factory=dict)
