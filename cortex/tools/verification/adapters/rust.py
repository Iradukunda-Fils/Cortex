"""
Rust Reference Emulator Trace Adapter
"""

import json
from typing import Any

from cortex.tools.verification.adapters.base import BaseAdapter
from cortex.tools.verification.schema import (
    CanonicalState,
    CanonicalSTCR,
    CanonicalTrap,
)


class RustAdapter(BaseAdapter):
    def parse_trace(self, trace_input: Any) -> list[CanonicalState]:
        if isinstance(trace_input, str):
            with open(trace_input) as f:
                data = json.load(f)
        else:
            data = trace_input

        canonical_steps = []
        for frame in data:
            step_id = frame.get("step_id", frame.get("step", 0))
            pc = frame.get("pc", 0)
            reg_hec = frame.get("reg_hec", 0)
            raw_inst = frame.get("instruction", {}).get("raw_hex", "0x00000000")

            outcome = frame.get("outcome", {})
            status = outcome.get("status", "OK")
            is_trap = (status == "EFF_TRAP")
            trap_cause_name = outcome.get("trap_cause", "None")
            dest_val = outcome.get("dest_reg_val", 0)

            trap_codes = {
                "None": 0,
                "InsufficientSpatialRights": 1,
                "EpochMismatch": 2,
                "InvalidCapability": 3,
                "IllegalInstruction": 15
            }
            cause_code = trap_codes.get(trap_cause_name, 1 if is_trap else 0)

            stcr_list = []
            for stcr in frame.get("stcr_file", []):
                stcr_list.append(CanonicalSTCR(
                    index=stcr.get("id", 0),
                    valid=stcr.get("valid", False),
                    permissions=stcr.get("spatial_mask", 0),
                    base_address=stcr.get("base_address", 0),
                    epoch=stcr.get("max_epoch", 0)
                ))

            canonical_steps.append(CanonicalState(
                step=step_id,
                pc=pc,
                instruction=raw_inst,
                privilege_mode="Machine",
                reg_hec=reg_hec,
                registers={"dest_val": f"0x{dest_val:016x}"},
                stcr=stcr_list,
                trap=CanonicalTrap(
                    triggered=is_trap,
                    cause_code=cause_code,
                    cause_name=trap_cause_name,
                    trap_val=dest_val
                )
            ))

        return canonical_steps
