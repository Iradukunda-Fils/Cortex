"""
RTL Verilator Driver for Hardware Telemetry & Trace Ingestion
"""

import os
import json
from tools.kernel.context import RuntimeContext
from tools.kernel.schema.event import RawRTLTraceEvent

class RTLVerilatorDriver:
    def __init__(self, context: RuntimeContext):
        self.context = context

    def ingest_trace_file(self, trace_json_path: str = "rtl_trace.json") -> int:
        if not os.path.exists(trace_json_path):
            fallback = "Research/artifacts/phase2/rtl_trace.json"
            if os.path.exists(fallback):
                trace_json_path = fallback

        with open(trace_json_path, "r") as f:
            data = json.load(f)

        frames = data.get("trace", [])
        for frame in frames:
            event = RawRTLTraceEvent(
                session_id=self.context.session_id,
                sequence_number=frame.get("step", 0),
                pc=frame.get("pc", 0),
                raw_instruction=frame.get("raw_instruction", "0x00000000"),
                eff_trap=frame.get("eff_trap", False),
                trap_cause=frame.get("trap_cause", 0),
                stcr_registers={idx: val for idx, val in enumerate(frame.get("stcr_registers", []))}
            )
            self.context.publish(event)

        return len(frames)
