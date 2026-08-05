"""
Verilator SystemVerilog RTL Trace Adapter
"""

import json
from typing import List, Dict, Any
from tools.verification.adapters.base import BaseAdapter
from tools.verification.schema import CanonicalState, CanonicalSTCR, CanonicalTrap

class RTLAdapter(BaseAdapter):
    def parse_trace(self, trace_input: Any) -> List[CanonicalState]:
        if isinstance(trace_input, str):
            with open(trace_input) as f:
                data = json.load(f)
        else:
            data = trace_input

        frames = data.get("trace", data) if isinstance(data, dict) else data

        canonical_steps = []
        for frame in frames:
            step_id = frame.get("step", 0)
            pc = frame.get("pc", 0)
            reg_hec = frame.get("reg_hec", 0)
            raw_inst = frame.get("raw_instruction", "0x00000000")
            is_trap = frame.get("eff_trap", False)
            cause_code = frame.get("trap_cause", 0)

            cause_names = {
                0: "None",
                1: "InsufficientSpatialRights",
                2: "EpochMismatch",
                3: "InvalidCapability",
                15: "IllegalInstruction"
            }
            cause_name = cause_names.get(cause_code, "UnknownTrap" if is_trap else "None")

            stcr_list = []
            raw_stcr_array = frame.get("stcr_registers", [])
            for reg_id, raw_hex in enumerate(raw_stcr_array):
                val = int(raw_hex, 16) if isinstance(raw_hex, str) else raw_hex
                valid = bool((val >> 63) & 1)
                perms = (val >> 48) & 0x7FFF
                base = (val >> 16) & 0xFFFFFFFF
                epoch = val & 0xFFFF

                stcr_list.append(CanonicalSTCR(
                    index=reg_id,
                    valid=valid,
                    permissions=perms,
                    base_address=base,
                    epoch=epoch
                ))

            canonical_steps.append(CanonicalState(
                step=step_id,
                pc=pc,
                instruction=raw_inst,
                privilege_mode="Machine",
                reg_hec=reg_hec,
                registers={},
                stcr=stcr_list,
                trap=CanonicalTrap(
                    triggered=is_trap,
                    cause_code=cause_code,
                    cause_name=cause_name,
                    trap_val=0
                )
            ))

        return canonical_steps
