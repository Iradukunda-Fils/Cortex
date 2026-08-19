"""
Cortex Replica Coordinate System (Phase 1)

Explicitly separates runtime worker execution coordinates (ExecutionIdentity)
from Gateway lease ownership coordinates (OwnershipIdentity).
"""

from dataclasses import dataclass


class StaleConfigGenerationError(Exception):
    """Raised when a worker operates under a stale ConfigGeneration (ERR_STALE_CONFIG_GENERATION)."""

    pass


@dataclass(frozen=True)
class ExecutionIdentity:
    """Uniquely identifies a specific worker execution attempt runtime coordinate.

    Every worker carries both a ReplicaGeneration (deployment wave) and a
    ConfigGeneration (immutable configuration snapshot version). The Gateway
    rejects workers whose config_generation does not match the active deployment.
    """

    group_id: str
    instance_id: str
    generation: int
    config_generation: int
    attempt_id: int

    def __post_init__(self) -> None:
        if not isinstance(self.group_id, str) or not self.group_id.strip():
            raise ValueError("group_id must be a non-empty string")
        if not isinstance(self.instance_id, str) or not self.instance_id.strip():
            raise ValueError("instance_id must be a non-empty string")
        if not isinstance(self.generation, int) or self.generation < 1:
            raise ValueError("generation must be a positive integer >= 1")
        if not isinstance(self.config_generation, int) or self.config_generation < 1:
            raise ValueError("config_generation must be a positive integer >= 1")
        if not isinstance(self.attempt_id, int) or self.attempt_id < 1:
            raise ValueError("attempt_id must be a positive integer >= 1")

    def coordinate_string(self) -> str:
        """Returns string representation for audit logs."""
        return f"{self.group_id}:{self.instance_id}:g{self.generation}:cfg{self.config_generation}:a{self.attempt_id}"


@dataclass(frozen=True)
class OwnershipIdentity:
    """Uniquely identifies Gateway authority and lease ownership for an invocation."""

    invocation_id: str
    lease_id: str
    lease_epoch: int

    def __post_init__(self) -> None:
        if not isinstance(self.invocation_id, str) or not self.invocation_id.strip():
            raise ValueError("invocation_id must be a non-empty string")
        if not isinstance(self.lease_id, str) or not self.lease_id.strip():
            raise ValueError("lease_id must be a non-empty string")
        if not isinstance(self.lease_epoch, int) or self.lease_epoch < 1:
            raise ValueError("lease_epoch must be a positive integer >= 1")

    def coordinate_string(self) -> str:
        """Returns string representation for audit logs."""
        return f"inv:{self.invocation_id}:lease:{self.lease_id}:ep{self.lease_epoch}"
