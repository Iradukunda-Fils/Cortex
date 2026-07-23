// Cortex Spatiotemporal Authority Core — Top Pipeline Interface
// Conforms strictly to SDS v1.0 Section 6.1

`timescale 1ns/1ps

module cortex_stcr_pipeline #(
    parameter int STCR_COUNT = 32,
    /* verilator lint_off UNUSEDPARAM */
    parameter int ADDR_WIDTH = 32
    /* verilator lint_on UNUSEDPARAM */
)(
    input  logic        clk,
    input  logic        rst_n,

    // Instruction Interface
    input  logic [31:0] inst_raw,
    input  logic        inst_valid,
    output logic        inst_ready,

    // Execution Controls & Exception Signals
    output logic        eff_trap,
    output logic [3:0]  trap_cause,
    output logic [63:0] trap_dest_val, // Must be 64'h0 on eff_trap (e_val ~ 0 invariant)

    // Global Epoch Unit State Output
    output logic [15:0] current_reg_hec
);

    // ------------------------------------------------------------------------
    // Internal Microarchitectural Registers
    // ------------------------------------------------------------------------
    logic [15:0] reg_hec;
    logic [63:0] stcr_file [0:STCR_COUNT-1];

    assign current_reg_hec = reg_hec;
    assign inst_ready      = 1'b1;

    // Decoding 32-Bit Instruction Layout (SDS v1.0 Section 4.1)
    wire [5:0]  opcode  = inst_raw[31:26];
    wire [4:0]  stcr_id = inst_raw[25:21];
    /* verilator lint_off UNUSEDSIGNAL */
    wire [4:0]  arg_reg = inst_raw[20:16];
    wire [15:0] imm16   = inst_raw[15:0];
    /* verilator lint_on UNUSEDSIGNAL */

    // STCR Field Unpacking (SDS v1.0 Layout)
    wire        stcr_v      = stcr_file[stcr_id][63];
    wire [14:0] stcr_mask   = stcr_file[stcr_id][62:48];
    wire [31:0] stcr_base   = stcr_file[stcr_id][47:16];
    wire [15:0] stcr_epoch  = stcr_file[stcr_id][15:0];

    // Guard Evaluation Logic (Combinational Guard Evaluation)
    logic guard_pass;
    logic [3:0] trap_code_internal;

    always_comb begin
        guard_pass = 1'b0;
        trap_code_internal = 4'h0;

        case (opcode)
            6'h01: begin // invoke_cap
                if (!stcr_v) begin
                    trap_code_internal = 4'h1; // Invalid Validity Bit
                end else if (reg_hec > stcr_epoch) begin
                    trap_code_internal = 4'h2; // Epoch Expired
                end else if ((stcr_mask & 15'h1000) == 15'h0) begin // Bit 12 = EXEC permission
                    trap_code_internal = 4'h1; // Insufficient Spatial Rights
                end else begin
                    guard_pass = 1'b1;
                end
            end
            6'h02: begin // grant_cap
                guard_pass = 1'b1;
            end
            6'h03: begin // restrict_cap
                guard_pass = 1'b1;
            end
            6'h04: begin // revoke_cap
                guard_pass = 1'b1;
            end
            6'h05: begin // hec.inc
                guard_pass = 1'b1;
            end
            default: begin
                trap_code_internal = 4'hF; // Reserved / Illegal Opcode Trap
            end
        endcase
    end

    // Sequential State Transition Logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            reg_hec <= 16'h0000;
            eff_trap <= 1'b0;
            trap_cause <= 4'h0;
            trap_dest_val <= 64'h0;
            for (int i = 0; i < STCR_COUNT; i++) begin
                stcr_file[i] <= 64'h0;
            end
            // Initial STCR0 descriptor matching initial capability setup (V=1, mask=0x7000, base=0x2000, epoch=0)
            stcr_file[0] <= 64'hf000000020000000;
        end else if (inst_valid) begin
            if (!guard_pass) begin
                // Synchronous Neutral Trap Execution (SDS v1.0 Section 5.2)
                eff_trap <= 1'b1;
                trap_cause <= trap_code_internal;
                trap_dest_val <= 64'h0; // Flush & zero destination
                stcr_file[stcr_id] <= 64'h0; // e_val ~ 0 zeroing
            end else begin
                eff_trap <= 1'b0;
                trap_cause <= 4'h0;

                case (opcode)
                    6'h02: begin // grant_cap
                        stcr_file[stcr_id] <= {1'b1, imm16[14:0], stcr_base, reg_hec};
                        trap_dest_val <= {1'b1, imm16[14:0], stcr_base, reg_hec};
                    end
                    6'h03: begin // restrict_cap: contract spatial_mask
                        stcr_file[stcr_id][62:48] <= stcr_mask & imm16[14:0];
                        trap_dest_val <= {stcr_v, stcr_mask & imm16[14:0], stcr_base, stcr_epoch};
                    end
                    6'h04: begin // revoke_cap: invalidate capability
                        stcr_file[stcr_id] <= 64'h0;
                        trap_dest_val <= 64'h0;
                    end
                    6'h05: begin // hec.inc: monotonic epoch advancement
                        reg_hec <= reg_hec + 1'b1;
                        trap_dest_val <= {48'h0, reg_hec + 1'b1};
                    end
                    default: begin
                        trap_dest_val <= {32'h0, stcr_base};
                    end
                endcase
            end
        end
    end

endmodule
