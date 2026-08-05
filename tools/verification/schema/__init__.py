"""
Typed Verification Schemas Package
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

@dataclass
class CanonicalSTCR:
    index: int
    valid: bool
    permissions: int
    base_address: int
    epoch: int

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class CanonicalTrap:
    triggered: bool
    cause_code: int
    cause_name: str
    trap_val: int

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class CanonicalState:
    step: int
    pc: int
    instruction: str
    privilege_mode: str
    reg_hec: int
    registers: Dict[str, str]
    stcr: List[CanonicalSTCR]
    trap: CanonicalTrap

    def to_dict(self) -> dict:
        d = asdict(self)
        d["stcr"] = [s.to_dict() for s in self.stcr]
        d["trap"] = self.trap.to_dict()
        return d
