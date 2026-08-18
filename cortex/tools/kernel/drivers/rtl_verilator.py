"""
RTL Verilator Driver for Hardware Telemetry & Trace Ingestion
"""

import json
import os
from typing import cast

from cortex.tools.kernel.context import RuntimeContext
from cortex.tools.kernel.schema.event import RawRTLTraceEvent


class RTLVerilatorDriver:
    context: RuntimeContext

    def __init__(self, context: RuntimeContext):
        self.context = context

    def ingest_trace_file(self, trace_json_path: str = "rtl_trace.json") -> int:
        if not os.path.exists(trace_json_path):
            fallback = "research/formalization/artifacts/phase2/rtl_trace.json"
            if os.path.exists(fallback):
                trace_json_path = fallback

        with open(trace_json_path, "r") as f:
            data = cast(dict[str, object], json.load(f))

        frames = cast(list[dict[str, object]], data.get("trace", []))
        for frame in frames:
            seq_num = int(cast(int | float, frame.get("step", 0)))
            pc_val = int(cast(int | float, frame.get("pc", 0)))
            raw_inst = str(frame.get("raw_instruction", "0x00000000"))
            eff_trap = bool(frame.get("eff_trap", False))
            trap_cause = int(cast(int | float, frame.get("trap_cause", 0)))
            stcr_list = cast(list[object], frame.get("stcr_registers", []))
            stcr_regs = {idx: str(val) for idx, val in enumerate(stcr_list)}

            event = RawRTLTraceEvent(
                session_id=self.context.session_id,
                sequence_number=seq_num,
                pc=pc_val,
                raw_instruction=raw_inst,
                eff_trap=eff_trap,
                trap_cause=trap_cause,
                stcr_registers=stcr_regs,
            )
            self.context.publish(event)

        return len(frames)
