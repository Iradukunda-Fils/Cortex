mod hardware;
mod isa;
mod trace;

use hardware::{GuardPipeline, HardwareEpochCounter, StcrFile, TrapCause};
use isa::{CapabilityDescriptor, Instruction, Opcode, spatial_rights};
use trace::{PostState, PreState, StepTraceRecord, TraceLogger};

pub struct SystemState {
    pub pc: u32,
    pub hec: HardwareEpochCounter,
    pub stcr_file: StcrFile,
    pub trap_flag: bool,
}

impl SystemState {
    pub fn new() -> Self {
        Self {
            pc: 0x00001000,
            hec: HardwareEpochCounter::new(),
            stcr_file: StcrFile::new(),
            trap_flag: false,
        }
    }
}

fn main() {
    println!("===========================================================");
    println!(" CORTEX SPATIOTEMPORAL EMULATOR v0.1.0 (SDS v1.0 Canonical)");
    println!("===========================================================");

    let mut state = SystemState::new();
    let mut logger = TraceLogger::new();

    // Setup initial valid capability in STCR 1
    let initial_cap = CapabilityDescriptor::new(
        true,
        spatial_rights::EXEC | spatial_rights::READ,
        0x00002000,
        10, // Max epoch = 10
    );
    state.stcr_file.write_descriptor(1, &initial_cap);

    println!("[INIT] Loaded STCR 1: {:?}", initial_cap);
    println!("[INIT] Initial REG_HEC = {}", state.hec.value());

    // Step 1: Valid Execution (REG_HEC = 0 <= 10)
    let raw_inst1 = (0x01u32 << 26) | (1u32 << 21) | (3u32 << 16) | 0x0000;
    execute_step(1, raw_inst1, &mut state, &mut logger);

    // Step 2: Increment Epoch (hec.inc) until epoch = 11 > 10
    for _ in 0..11 {
        let raw_hec_inc = 0x05u32 << 26;
        execute_step(2, raw_hec_inc, &mut state, &mut logger);
    }
    println!("[EVENT] Advanced REG_HEC to {}", state.hec.value());

    // Step 3: Expired Execution Attempt (REG_HEC = 11 > 10) -> TRAP
    execute_step(3, raw_inst1, &mut state, &mut logger);

    println!("\n--- Step-by-Step Refinement Trace (JSON) ---");
    if let Ok(json) = logger.to_json_string() {
        println!("{}", json);
    }
}

fn execute_step(
    step_num: u64,
    raw_inst: u32,
    state: &mut SystemState,
    logger: &mut TraceLogger,
) {
    let inst = Instruction::decode(raw_inst);
    let pre_hec = state.hec.value();
    let stcr_raw = state.stcr_file.read_raw(inst.stcr_id as usize);
    let stcr_decoded = state.stcr_file.read_descriptor(inst.stcr_id as usize);

    let mut guard_result = "PASS".to_string();
    let mut trap_cause: Option<TrapCause> = None;

    match inst.opcode {
        Ok(Opcode::InvokeCap) => {
            let req_perm = spatial_rights::EXEC;
            match GuardPipeline::evaluate_invoke(stcr_decoded.as_ref(), req_perm, pre_hec) {
                Ok(()) => {
                    if let Some(ref cap) = stcr_decoded {
                        state.pc = cap.base_address;
                    }
                }
                Err(cause) => {
                    guard_result = "TRAP".to_string();
                    trap_cause = Some(cause);
                    state.trap_flag = true;
                    state.stcr_file.zero_register(inst.stcr_id as usize); // e_val 0 neutral trap write
                }
            }
        }
        Ok(Opcode::HecInc) => {
            let _ = state.hec.increment();
        }
        Ok(Opcode::RestrictCap) => {
            if let Some(mut cap) = stcr_decoded {
                cap.spatial_mask &= inst.immediate;
                state.stcr_file.write_descriptor(inst.stcr_id as usize, &cap);
            }
        }
        Ok(Opcode::RevokeCap) => {
            state.stcr_file.zero_register(inst.stcr_id as usize);
        }
        Ok(Opcode::GrantCap) => {
            // Memory descriptor write simulated
        }
        Err(reserved_code) => {
            guard_result = "TRAP".to_string();
            trap_cause = Some(TrapCause::ReservedOpcode(reserved_code));
            state.trap_flag = true;
            state.stcr_file.zero_register(inst.stcr_id as usize);
        }
    }

    logger.log_step(StepTraceRecord {
        step: step_num,
        instruction: format!("{:?}", inst.opcode),
        pre_state: PreState {
            reg_hec: pre_hec,
            stcr_raw: format!("{:#018x}", stcr_raw),
            stcr_decoded,
        },
        guard_result,
        post_state: PostState {
            pc: format!("{:#010x}", state.pc),
            trap_flag: state.trap_flag,
            trap_cause,
        },
    });
}
