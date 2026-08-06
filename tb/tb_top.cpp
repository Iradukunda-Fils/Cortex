// Cortex Spatiotemporal Authority Core — Verilator C++ Simulation Harness
// Target Module: cortex_stcr_pipeline.sv
// Artifact Output: rtl_trace.json

#include <iostream>
#include <fstream>
#include <vector>
#include <iomanip>
#include <cstdint>
#include <verilated.h>
#include "Vcortex_stcr_pipeline.h"
#include "Vcortex_stcr_pipeline___024root.h"

struct TraceStep {
    uint64_t step_idx;
    uint32_t pc;
    uint32_t raw_instruction;
    uint16_t reg_hec;
    bool eff_trap;
    uint8_t trap_cause;
    uint64_t stcr_file[32];
};

void export_rtl_trace(const std::string& filename, const std::vector<TraceStep>& trace) {
    std::ofstream out(filename);
    out << "{\n";
    out << "  \"engine\": \"verilator_rtl\",\n";
    out << "  \"total_steps\": " << trace.size() << ",\n";
    out << "  \"trace\": [\n";

    for (size_t i = 0; i < trace.size(); ++i) {
        const auto& s = trace[i];
        out << "    {\n";
        out << "      \"step\": " << s.step_idx + 1 << ",\n";
        out << "      \"pc\": " << std::dec << s.pc << ",\n";
        out << "      \"raw_instruction\": \"0x" << std::hex << std::setw(8) << std::setfill('0') << s.raw_instruction << "\",\n";
        out << "      \"reg_hec\": " << std::dec << s.reg_hec << ",\n";
        out << "      \"eff_trap\": " << (s.eff_trap ? "true" : "false") << ",\n";
        out << "      \"trap_cause\": " << static_cast<int>(s.trap_cause) << ",\n";
        out << "      \"stcr_registers\": [\n";
        for (int r = 0; r < 32; ++r) {
            out << "        \"0x" << std::hex << std::setw(16) << std::setfill('0') << s.stcr_file[r] << "\""
                << (r < 31 ? ",\n" : "\n");
        }
        out << "      ]\n";
        out << "    }" << (i < trace.size() - 1 ? ",\n" : "\n");
    }
    out << "  ]\n";
    out << "}\n";
    out.close();
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    auto top = std::make_unique<Vcortex_stcr_pipeline>();

    std::string bin_path = "Research/artifacts/phase1_5/canonical_test_program.bin";
    std::string out_path = "rtl_trace.json";

    if (argc > 1) bin_path = argv[1];
    if (argc > 2) out_path = argv[2];

    std::ifstream bin_file(bin_path, std::ios::binary);
    if (!bin_file.is_open()) {
        std::cerr << "FATAL: Could not open input binary: " << bin_path << std::endl;
        return 1;
    }

    std::vector<uint32_t> program;
    char header_buf[12];
    if (bin_file.read(header_buf, 12)) {
        uint32_t inst = 0;
        while (bin_file.read(reinterpret_cast<char*>(&inst), sizeof(inst))) {
            program.push_back(__builtin_bswap32(inst));
        }
    }
    bin_file.close();

    // Reset System
    top->clk = 0;
    top->rst_n = 0;
    top->inst_valid = 0;
    top->eval();
    
    top->clk = 1;
    top->eval();
    top->rst_n = 1;
    top->eval();

    std::vector<TraceStep> execution_trace;
    uint64_t step_counter = 0;
    size_t inst_idx = 0;

    // Run until all program instructions retire through Writeback
    int cycle_count = 0;
    const int max_cycles = 1000;

    while (execution_trace.size() < program.size() && cycle_count < max_cycles) {
        cycle_count++;

        uint16_t pre_hec = top->current_reg_hec;
        uint64_t pre_stcr[32];
        for (int r = 0; r < 32; ++r) {
            pre_stcr[r] = top->rootp->cortex_stcr_pipeline__DOT__stcr_file[r];
        }

        // Feed instruction if available
        if (inst_idx < program.size()) {
            top->inst_raw = program[inst_idx];
            top->inst_valid = 1;
            inst_idx++;
        } else {
            top->inst_valid = 0;
        }

        // Clock edge low -> high
        top->clk = 0;
        top->eval();
        top->clk = 1;
        top->eval();

        // Sample state frame only when instruction retires at Writeback boundary
        if (top->wb_inst_retired) {
            TraceStep step;
            step.step_idx = step_counter++;
            step.pc = top->wb_pc;
            step.raw_instruction = top->wb_inst_raw;
            step.reg_hec = pre_hec;
            step.eff_trap = top->eff_trap;
            step.trap_cause = top->trap_cause;

            for (int r = 0; r < 32; ++r) {
                step.stcr_file[r] = pre_stcr[r];
            }

            execution_trace.push_back(step);
        }
    }

    export_rtl_trace(out_path, execution_trace);
    std::cout << "SUCCESS: Verilator 4-stage pipeline simulation complete. Emitted " 
              << execution_trace.size() << " retired commit frames to " << out_path << std::endl;

    return 0;
}
