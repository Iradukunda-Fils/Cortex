"""
First-Class Workflow Primitive & Policy Schema
"""

import enum
import time
import uuid
from dataclasses import dataclass, field


class WorkflowState(str, enum.Enum):
    """Lifecycle state of a Cortex workflow execution.

    Transitions: PENDING → RUNNING → COMPLETED | FAILED | ABORTED
    """

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
    root_intent_id: str | None = None
    execution_graph_id: str | None = None
    created_at_ns: int = field(default_factory=lambda: time.time_ns())
    metadata: dict[str, object] = field(default_factory=dict)
