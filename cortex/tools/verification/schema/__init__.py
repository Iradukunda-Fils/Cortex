"""
Typed Verification Schemas Package
"""

__all__: list[str] = []


from dataclasses import asdict, dataclass


@dataclass
class CanonicalSTCR:
    index: int
    valid: bool
    permissions: int
    base_address: int
    epoch: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

@dataclass
class CanonicalTrap:
    triggered: bool
    cause_code: int
    cause_name: str
    trap_val: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

@dataclass
class CanonicalState:
    step: int
    pc: int
    instruction: str
    privilege_mode: str
    reg_hec: int
    registers: dict[str, str]
    stcr: list[CanonicalSTCR]
    trap: CanonicalTrap

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["stcr"] = [s.to_dict() for s in self.stcr]
        d["trap"] = self.trap.to_dict()
        return d
