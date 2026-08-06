// Cortex Spatiotemporal Authority Core — 4-Stage Pipelined Architecture (IF/ID/EX/WB)
// Conforms strictly to CommitContractV1 Writeback Retirement Boundary

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

    // Writeback Commit Interface (CommitContractV1 Boundary)
    output logic        wb_inst_retired,
    output logic [31:0] wb_pc,
    output logic [31:0] wb_inst_raw,

    // Execution Controls & Exception Signals
    output logic        eff_trap,
    output logic [3:0]  trap_cause,
    output logic [63:0] trap_dest_val, // 64'h0 on eff_trap (e_val ~ 0 invariant)

    // Global Epoch Unit State Output
    output logic [15:0] current_reg_hec
);

    // ------------------------------------------------------------------------
    // Architectural State Registers
    // ------------------------------------------------------------------------
    logic [15:0] reg_hec;
    logic [63:0] stcr_file [0:STCR_COUNT-1];

    assign current_reg_hec = reg_hec;

    // ------------------------------------------------------------------------
    // Pipeline Stage Registers
    // ------------------------------------------------------------------------
    
    // IF/ID Pipeline Register
    typedef struct packed {
        logic [31:0] pc;
        logic [31:0] inst_raw;
        logic        valid;
    } if_id_reg_t;

    if_id_reg_t if_id_reg;

    // ID/EX Pipeline Register
    typedef struct packed {
        logic [31:0] pc;
        logic [31:0] inst_raw;
        logic [5:0]  opcode;
        logic [4:0]  stcr_id;
        logic [15:0] imm16;
        logic [63:0] stcr_val;
        logic        valid;
    } id_ex_reg_t;

    id_ex_reg_t id_ex_reg;

    // EX/WB Pipeline Register
    /* verilator lint_off UNUSEDSIGNAL */
    typedef struct packed {
        logic [31:0] pc;
        logic [31:0] inst_raw;
        logic [5:0]  opcode;
        logic [4:0]  stcr_id;
        logic [15:0] imm16;
        logic [63:0] result_val;
        logic        guard_pass;
        logic [3:0]  trap_code;
        logic        valid;
    } ex_wb_reg_t;

    ex_wb_reg_t ex_wb_reg;
    /* verilator lint_on UNUSEDSIGNAL */

    // ------------------------------------------------------------------------
    // Forwarding & Hazard Unit Logic
    // ------------------------------------------------------------------------
    wire [4:0] id_stcr_id = inst_raw[25:21];
    logic [63:0] forwarded_stcr_val;

    always_comb begin
        // Default read from register file
        forwarded_stcr_val = stcr_file[id_stcr_id];

        // Forwarding from EX stage if valid writeback pending
        if (ex_wb_reg.valid && ex_wb_reg.guard_pass && (ex_wb_reg.stcr_id == id_stcr_id)) begin
            forwarded_stcr_val = ex_wb_reg.result_val;
        end
        // Forwarding from ID/EX stage
        else if (id_ex_reg.valid && (id_ex_reg.stcr_id == id_stcr_id)) begin
            forwarded_stcr_val = id_ex_reg.stcr_val;
        end
    end

    assign inst_ready = 1'b1;

    // ------------------------------------------------------------------------
    // Stage 1: Instruction Fetch (IF)
    // ------------------------------------------------------------------------
    logic [31:0] if_pc;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            if_pc <= 32'h00001000;
            if_id_reg <= '0;
        end else if (inst_valid) begin
            if_id_reg.pc <= if_pc;
            if_id_reg.inst_raw <= inst_raw;
            if_id_reg.valid <= 1'b1;
            if_pc <= if_pc + 32'd4;
        end else begin
            if_id_reg.valid <= 1'b0;
        end
    end

    // ------------------------------------------------------------------------
    // Stage 2: Instruction Decode (ID)
    // ------------------------------------------------------------------------
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            id_ex_reg <= '0;
        end else begin
            if (if_id_reg.valid) begin
                id_ex_reg.pc <= if_id_reg.pc;
                id_ex_reg.inst_raw <= if_id_reg.inst_raw;
                id_ex_reg.opcode <= if_id_reg.inst_raw[31:26];
                id_ex_reg.stcr_id <= if_id_reg.inst_raw[25:21];
                id_ex_reg.imm16 <= if_id_reg.inst_raw[15:0];
                id_ex_reg.stcr_val <= forwarded_stcr_val;
                id_ex_reg.valid <= 1'b1;
            end else begin
                id_ex_reg.valid <= 1'b0;
            end
        end
    end

    // ------------------------------------------------------------------------
    // Stage 3: Execution & Guard Check (EX)
    // ------------------------------------------------------------------------
    wire        ex_stcr_v      = id_ex_reg.stcr_val[63];
    wire [14:0] ex_stcr_mask   = id_ex_reg.stcr_val[62:48];
    wire [31:0] ex_stcr_base   = id_ex_reg.stcr_val[47:16];
    wire [15:0] ex_stcr_epoch  = id_ex_reg.stcr_val[15:0];

    logic ex_guard_pass;
    logic [3:0] ex_trap_code;
    logic [63:0] ex_result_val;

    always_comb begin
        ex_guard_pass = 1'b0;
        ex_trap_code = 4'h0;
        ex_result_val = 64'h0;

        case (id_ex_reg.opcode)
            6'h01: begin // invoke_cap
                if (!ex_stcr_v) begin
                    ex_trap_code = 4'h1;
                end else if (reg_hec > ex_stcr_epoch) begin
                    ex_trap_code = 4'h2;
                end else if ((ex_stcr_mask & 15'h1000) == 15'h0) begin
                    ex_trap_code = 4'h1;
                end else begin
                    ex_guard_pass = 1'b1;
                    ex_result_val = {32'h0, ex_stcr_base};
                end
            end
            6'h02: begin // grant_cap
                ex_guard_pass = 1'b1;
                ex_result_val = {1'b1, id_ex_reg.imm16[14:0], ex_stcr_base, reg_hec};
            end
            6'h03: begin // restrict_cap
                ex_guard_pass = 1'b1;
                ex_result_val = {ex_stcr_v, ex_stcr_mask & id_ex_reg.imm16[14:0], ex_stcr_base, ex_stcr_epoch};
            end
            6'h04: begin // revoke_cap
                ex_guard_pass = 1'b1;
                ex_result_val = 64'h0;
            end
            6'h05: begin // hec.inc
                ex_guard_pass = 1'b1;
                ex_result_val = {48'h0, reg_hec + 1'b1};
            end
            default: begin
                ex_trap_code = 4'hF;
            end
        endcase
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ex_wb_reg <= '0;
        end else begin
            if (id_ex_reg.valid) begin
                ex_wb_reg.pc <= id_ex_reg.pc;
                ex_wb_reg.inst_raw <= id_ex_reg.inst_raw;
                ex_wb_reg.opcode <= id_ex_reg.opcode;
                ex_wb_reg.stcr_id <= id_ex_reg.stcr_id;
                ex_wb_reg.imm16 <= id_ex_reg.imm16;
                ex_wb_reg.result_val <= ex_result_val;
                ex_wb_reg.guard_pass <= ex_guard_pass;
                ex_wb_reg.trap_code <= ex_trap_code;
                ex_wb_reg.valid <= 1'b1;
            end else begin
                ex_wb_reg.valid <= 1'b0;
            end
        end
    end

    // ------------------------------------------------------------------------
    // Stage 4: Writeback & Commit (WB) — CommitContractV1 Retirement Boundary
    // ------------------------------------------------------------------------
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            reg_hec <= 16'h0000;
            eff_trap <= 1'b0;
            trap_cause <= 4'h0;
            trap_dest_val <= 64'h0;
            wb_inst_retired <= 1'b0;
            wb_pc <= 32'h0;
            wb_inst_raw <= 32'h0;
            for (int i = 0; i < STCR_COUNT; i++) begin
                stcr_file[i] <= 64'h0;
            end
            stcr_file[0] <= 64'hf000000020000000;
        end else begin
            if (ex_wb_reg.valid) begin
                wb_inst_retired <= 1'b1;
                wb_pc <= ex_wb_reg.pc;
                wb_inst_raw <= ex_wb_reg.inst_raw;

                if (!ex_wb_reg.guard_pass) begin
                    eff_trap <= 1'b1;
                    trap_cause <= ex_wb_reg.trap_code;
                    trap_dest_val <= 64'h0;
                    stcr_file[ex_wb_reg.stcr_id] <= 64'h0;
                end else begin
                    eff_trap <= 1'b0;
                    trap_cause <= 4'h0;
                    trap_dest_val <= ex_wb_reg.result_val;

                    case (ex_wb_reg.opcode)
                        6'h02: stcr_file[ex_wb_reg.stcr_id] <= ex_wb_reg.result_val;
                        6'h03: stcr_file[ex_wb_reg.stcr_id] <= ex_wb_reg.result_val;
                        6'h04: stcr_file[ex_wb_reg.stcr_id] <= 64'h0;
                        6'h05: reg_hec <= reg_hec + 1'b1;
                        default: ;
                    endcase
                end
            end else begin
                wb_inst_retired <= 1'b0;
            end
        end
    end

endmodule
