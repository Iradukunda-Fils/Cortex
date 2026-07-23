#!/usr/bin/env python3
"""
Coq-to-Rust Refinement Differential Verification Harness
Enforces R_refine step-by-step equivalence between Coq operational traces and Rust emulator JSON logs.
"""

import json
import sys
from pathlib import Path

def assert_step_equivalence(step_coq: dict, step_emu: dict, step_idx: int):
    # 1. Monotonic Global Epoch Equivalence
    assert step_coq["reg_hec"] == step_emu["reg_hec"], \
        f"[Step {step_idx}] HEC Discrepancy: Coq={step_coq['reg_hec']}, Emulator={step_emu['reg_hec']}"

    # 2. Synchronous Trap & Status Equivalence
    assert step_coq["outcome"]["status"] == step_emu["outcome"]["status"], \
        f"[Step {step_idx}] Status Divergence: Coq={step_coq['outcome']['status']}, Emulator={step_emu['outcome']['status']}"

    # 3. Destination Neutrality (e_val ~ 0 on trap or deterministic result commit)
    assert step_coq["outcome"]["dest_reg_val"] == step_emu["outcome"]["dest_reg_val"], \
        f"[Step {step_idx}] Result Value Mismatch: Coq={step_coq['outcome']['dest_reg_val']}, Emulator={step_emu['outcome']['dest_reg_val']}"

    # 4. Capability Register File Equivalence (R_refine mapping check)
    coq_stcrs = {c["id"]: c for c in step_coq["stcr_file"]}
    emu_stcrs = {c["id"]: c for c in step_emu["stcr_file"]}

    for reg_id in range(32):
        c_cap, e_cap = coq_stcrs[reg_id], emu_stcrs[reg_id]
        assert c_cap["valid"] == e_cap["valid"], f"[Step {step_idx}] STCR[{reg_id}].V mismatch"
        if c_cap["valid"]:
            assert c_cap["spatial_mask"] == e_cap["spatial_mask"], f"[Step {step_idx}] STCR[{reg_id}].Spatial_Mask mismatch"
            assert c_cap["base_address"] == e_cap["base_address"], f"[Step {step_idx}] STCR[{reg_id}].Base_Address mismatch"
            assert c_cap["max_epoch"] == e_cap["max_epoch"], f"[Step {step_idx}] STCR[{reg_id}].Max_Epoch mismatch"

def main():
    if len(sys.argv) < 3:
        print("Usage: diff_harness.py <coq_trace.json> <emulator_trace.json>")
        sys.exit(1)

    coq_trace_path = Path(sys.argv[1])
    emu_trace_path = Path(sys.argv[2])

    if not coq_trace_path.exists():
        print(f"Error: Coq trace file not found: {coq_trace_path}")
        sys.exit(1)

    if not emu_trace_path.exists():
        print(f"Error: Emulator trace file not found: {emu_trace_path}")
        sys.exit(1)

    coq_trace = json.loads(coq_trace_path.read_text())
    emu_trace = json.loads(emu_trace_path.read_text())

    assert len(coq_trace) == len(emu_trace), \
        f"Trace length mismatch: Coq emitted {len(coq_trace)} steps, Emulator emitted {len(emu_trace)} steps"

    print(f"[+] Verifying {len(coq_trace)} execution steps for strict refinement equivalence...")
    for idx, (c_step, e_step) in enumerate(zip(coq_trace, emu_trace)):
        assert_step_equivalence(c_step, e_step, idx + 1)

    print("==========================================================================")
    print(" SUCCESS: Refinement Equivalence Confirmed between Coq & Rust Emulator!")
    print("==========================================================================")

if __name__ == "__main__":
    main()
