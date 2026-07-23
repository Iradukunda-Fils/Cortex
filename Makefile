# Cortex Spatiotemporal Authority Framework Makefile
# Handles Verilator RTL compilation, binary generation, and 3-way trace verification

VERILATOR ?= verilator
PYTHON ?= python3
CARGO ?= cargo

RTL_SRC = rtl/cortex_stcr_pipeline.sv
TB_SRC = tb/tb_top.cpp
BIN_SRC = Research/artifacts/phase1_5/canonical_test_program.bin

BUILD_DIR = obj_dir
VERILATOR_FLAGS = -Wall --cc $(RTL_SRC) --exe $(TB_SRC) -Mdir $(BUILD_DIR) --build -j 0

.PHONY: all verilate test clean

all: verilate

# 1. Compile SystemVerilog RTL and C++ Testbench with Verilator
verilate: $(RTL_SRC) $(TB_SRC)
	@if command -v $(VERILATOR) >/dev/null 2>&1; then \
		echo "[+] Compiling SystemVerilog RTL with Verilator..."; \
		$(VERILATOR) $(VERILATOR_FLAGS); \
	else \
		echo "[!] Warning: verilator binary not found in PATH. Install verilator to build RTL target."; \
	fi

# 2. Run RTL simulation against canonical test binary
run-rtl: verilate
	@if [ -f $(BUILD_DIR)/Vcortex_stcr_pipeline ]; then \
		echo "[+] Running Verilator RTL simulation..."; \
		./$(BUILD_DIR)/Vcortex_stcr_pipeline $(BIN_SRC) rtl_trace.json; \
	fi

# 3. Full 3-Way Differential Refinement Verification
test-refinement: run-rtl
	@echo "[+] Running 3-Way Differential Trace Verifier..."
	$(PYTHON) cortex-emulator/tests/diff_harness.py \
		Research/artifacts/phase1_5/coq_trace.json \
		Research/artifacts/phase1_5/emulator_trace.json \
		rtl_trace.json

clean:
	rm -rf $(BUILD_DIR) rtl_trace.json
