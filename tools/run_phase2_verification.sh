#!/usr/bin/env bash
# Cortex Spatiotemporal Authority Core — Phase 2 Audit Verification Runner
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

echo "[+] Building SystemVerilog RTL and C++ Testbench with Verilator..."
make verilate

echo "[+] Running Verilator RTL Simulation against canonical payload..."
make run-rtl

echo "[+] Running 3-Way Differential Trace Equivalence Verifier..."
python3 cortex-emulator/tests/diff_harness.py \
  Research/artifacts/phase2/coq_trace.json \
  Research/artifacts/phase2/emulator_trace.json \
  rtl_trace.json
