"""
Frozen CommitEventV1 Schema for Architectural Retirement Events
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any

@dataclass(frozen=True)
class PureArchitecturalStateV1:
    pc: str
    instruction: str
    privilege_mode: str
    registers: Dict[str, str]
    stcr: List[Dict[str, Any]]
    trap: Dict[str, Any]
    memory_commit: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass(frozen=True)
class ObservationMetadataV1:
    step: int
    cycle: int
    timestamp_ns: int
    target_name: str
    commit_id: str
    adapter_version: str

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass(frozen=True)
class CommitEventV1:
    schema_version: int = 1
    architectural: PureArchitecturalStateV1 = None
    observation: ObservationMetadataV1 = None

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "architectural": self.architectural.to_dict() if self.architectural else {},
            "observation": self.observation.to_dict() if self.observation else {}
        }
