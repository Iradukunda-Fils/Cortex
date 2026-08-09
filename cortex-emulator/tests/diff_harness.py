#!/usr/bin/env python3
"""
3-Way Coq-to-Rust-to-RTL Refinement Differential Verification Harness
Enforces R_refine step-by-step state equivalence across Coq, Rust emulator, and SystemVerilog RTL.
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

def assert_rtl_step_equivalence(step_emu: dict, step_rtl: dict, step_idx: int):
    # 1. Epoch Counter Check
    assert step_emu["reg_hec"] == step_rtl["reg_hec"], \
        f"[Step {step_idx}] RTL HEC Discrepancy: Emulator={step_emu['reg_hec']}, RTL={step_rtl['reg_hec']}"

    # 2. Trap Status Check
    is_emu_trap = (step_emu["outcome"]["status"] == "EFF_TRAP")
    assert is_emu_trap == step_rtl["eff_trap"], \
        f"[Step {step_idx}] RTL Trap Divergence: Emulator Trap={is_emu_trap}, RTL eff_trap={step_rtl['eff_trap']}"

    # 3. 32x 64-Bit STCR File Decoding & Strict Field Comparison
    emu_stcrs = {c["id"]: c for c in step_emu["stcr_file"]}
    rtl_stcr_raw = step_rtl["stcr_registers"]

    for reg_id in range(32):
        raw_val = int(rtl_stcr_raw[reg_id], 16)
        r_valid = ((raw_val >> 63) & 1) == 1
        r_mask = (raw_val >> 48) & 0x7FFF
        r_base = (raw_val >> 16) & 0xFFFFFFFF
        r_epoch = raw_val & 0xFFFF

        e_cap = emu_stcrs[reg_id]
        assert e_cap["valid"] == r_valid, f"[Step {step_idx}] RTL STCR[{reg_id}].valid mismatch: Emu={e_cap['valid']}, RTL={r_valid}"
        if e_cap["valid"]:
            assert e_cap["spatial_mask"] == r_mask, f"[Step {step_idx}] RTL STCR[{reg_id}].spatial_mask mismatch: Emu={e_cap['spatial_mask']}, RTL={r_mask}"
            assert e_cap["base_address"] == r_base, f"[Step {step_idx}] RTL STCR[{reg_id}].base_address mismatch: Emu={e_cap['base_address']}, RTL={r_base}"
            assert e_cap["max_epoch"] == r_epoch, f"[Step {step_idx}] RTL STCR[{reg_id}].max_epoch mismatch: Emu={e_cap['max_epoch']}, RTL={r_epoch}"

def main():
    if len(sys.argv) < 3:
        print("Usage: diff_harness.py <coq_trace.json> <emulator_trace.json> [rtl_trace.json]")
        sys.exit(1)

    coq_trace_path = Path(sys.argv[1])
    emu_trace_path = Path(sys.argv[2])
    rtl_trace_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None

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

    print(f"[+] Verifying {len(coq_trace)} execution steps for 2-way (Coq <-> Rust) refinement equivalence...")
    for idx, (c_step, e_step) in enumerate(zip(coq_trace, emu_trace)):
        assert_step_equivalence(c_step, e_step, idx + 1)

    print("    [MATCH] Coq <-> Rust Emulator 1:1 State Equivalence Confirmed.")

    if rtl_trace_path and rtl_trace_path.exists():
        rtl_data = json.loads(rtl_trace_path.read_text())
        rtl_trace = rtl_data.get("trace", rtl_data)
        assert len(emu_trace) == len(rtl_trace), \
            f"RTL Trace length mismatch: Emulator emitted {len(emu_trace)} steps, RTL emitted {len(rtl_trace)} steps"

        print(f"[+] Verifying {len(rtl_trace)} execution steps for 3-way (Rust <-> RTL) refinement equivalence...")
        for idx, (e_step, r_step) in enumerate(zip(emu_trace, rtl_trace)):
            assert_rtl_step_equivalence(e_step, r_step, idx + 1)
        print("    [MATCH] Rust Emulator <-> Verilator SystemVerilog RTL 1:1 State Equivalence Confirmed.")

    print("==========================================================================")
    print(" SUCCESS: Refinement Equivalence Confirmed Across Evaluated Targets!")
    print("==========================================================================")

if __name__ == "__main__":
    main()
