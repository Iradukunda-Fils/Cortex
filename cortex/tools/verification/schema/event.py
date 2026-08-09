"""
Frozen CommitEventV1 Schema for Architectural Retirement Events
"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PureArchitecturalStateV1:
    pc: str
    instruction: str
    privilege_mode: str
    registers: dict[str, str]
    stcr: list[dict[str, object]]
    trap: dict[str, object]
    memory_commit: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

@dataclass(frozen=True)
class ObservationMetadataV1:
    step: int
    cycle: int
    timestamp_ns: int
    target_name: str
    commit_id: str
    adapter_version: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

@dataclass(frozen=True)
class CommitEventV1:
    schema_version: int = 1
    architectural: PureArchitecturalStateV1 | None = None
    observation: ObservationMetadataV1 | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "architectural": self.architectural.to_dict() if self.architectural else {},
            "observation": self.observation.to_dict() if self.observation else {}
        }
