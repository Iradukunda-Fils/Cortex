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

// Struct mirroring trace_schema.json frame fields
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
        out << "      \"pc\": " << s.pc << ",\n";
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

    if (argc > 1) {
        bin_path = argv[1];
    }
    if (argc > 2) {
        out_path = argv[2];
    }

    // Read canonical test binary
    std::ifstream bin_file(bin_path, std::ios::binary);
    if (!bin_file.is_open()) {
        std::cerr << "FATAL: Could not open input binary: " << bin_path << std::endl;
        return 1;
    }

    std::vector<uint32_t> program;
    // Skip 12-byte header (6B magic + 2B version + 4B count) if matching CORTEX-v1 spec
    char header_buf[12];
    if (bin_file.read(header_buf, 12)) {
        uint32_t inst = 0;
        while (bin_file.read(reinterpret_cast<char*>(&inst), sizeof(inst))) {
            program.push_back(__builtin_bswap32(inst));
        }
    }
    bin_file.close();

    // System Reset Sequence
    top->clk = 0;
    top->rst_n = 0;
    top->inst_valid = 0;
    top->eval();
    
    top->clk = 1;
    top->eval();
    top->rst_n = 1;
    top->eval();

    std::vector<TraceStep> execution_trace;
    uint32_t current_pc = 0x00001000;
    uint64_t step_counter = 0;

    // Simulation Loop
    for (size_t i = 0; i < program.size(); ++i) {
        top->inst_raw = program[i];
        top->inst_valid = 1;

        // Drive clock edge low -> high
        top->clk = 0;
        top->eval();
        top->clk = 1;
        top->eval();

        // Sample state frame post-edge
        TraceStep step;
        step.step_idx = step_counter++;
        step.pc = current_pc;
        step.raw_instruction = program[i];
        step.reg_hec = top->current_reg_hec;
        step.eff_trap = top->eff_trap;
        step.trap_cause = top->trap_cause;

        // Extract 32x 64-bit STCR state directly from Verilated root scope
        for (int r = 0; r < 32; ++r) {
            step.stcr_file[r] = top->rootp->cortex_stcr_pipeline__DOT__stcr_file[r];
        }

        execution_trace.push_back(step);
        current_pc += 4;
    }

    export_rtl_trace(out_path, execution_trace);
    std::cout << "SUCCESS: Verilator simulation complete. Emitted " 
              << execution_trace.size() << " trace frames to " << out_path << std::endl;

    return 0;
}
