pub mod cbe;
mod hardware;
mod isa;
mod loader;
mod trace;

use hardware::{GuardPipeline, HardwareEpochCounter, StcrFile, TrapCause};
use isa::{spatial_rights, CapabilityDescriptor, Instruction, Opcode};
use loader::load_program;
use std::env;
use std::fs;
use trace::{InstructionTrace, OutcomeTrace, StcrState, StepTraceRecord, TraceLogger};

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

impl Default for SystemState {
    fn default() -> Self {
        Self::new()
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let mut export_path: Option<String> = None;
    let mut bin_path: Option<String> = None;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--export-trace" | "--trace-out" if i + 1 < args.len() => {
                export_path = Some(args[i + 1].clone());
                i += 1;
            }
            "--bin" | "-b" if i + 1 < args.len() => {
                bin_path = Some(args[i + 1].clone());
                i += 1;
            }
            arg if !arg.starts_with('-') => {
                bin_path = Some(arg.to_string());
            }
            _ => {}
        }
        i += 1;
    }

    let mut state = SystemState::new();
    let mut logger = TraceLogger::new();

    // Setup initial valid capability in STCR 0 for testing (Max epoch = 0)
    let initial_cap = CapabilityDescriptor::new(
        true,
        spatial_rights::EXEC | spatial_rights::READ | spatial_rights::WRITE,
        0x00002000,
        0, // Max epoch = 0
    );
    state.stcr_file.write_descriptor(0, &initial_cap);

    if let Some(path) = bin_path {
        println!("[+] Loading binary execution program from: {}", path);
        match load_program(&path) {
            Ok(program) => {
                println!(
                    "[+] Successfully loaded {} instructions",
                    program.instruction_count
                );
                for (idx, inst) in program.instructions.into_iter().enumerate() {
                    execute_step(idx + 1, inst, &mut state, &mut logger);
                }
            }
            Err(err) => {
                eprintln!("[-] Error loading binary: {}", err);
                std::process::exit(1);
            }
        }
    } else {
        // Fallback default demonstration loop
        let raw_inst1 = (0x01u32 << 26) | (1u32 << 16);
        execute_step(1, Instruction::decode(raw_inst1), &mut state, &mut logger);

        for step_idx in 2..=12 {
            let raw_hec_inc = 0x05u32 << 26;
            execute_step(
                step_idx,
                Instruction::decode(raw_hec_inc),
                &mut state,
                &mut logger,
            );
        }

        execute_step(13, Instruction::decode(raw_inst1), &mut state, &mut logger);
    }

    if let Ok(json) = logger.to_json_string() {
        if let Some(path) = export_path {
            let _ = fs::write(&path, &json);
            println!("[+] Exported trace to {}", path);
        } else {
            println!("{}", json);
        }
    }
}

fn execute_step(
    step_num: usize,
    inst: Instruction,
    state: &mut SystemState,
    logger: &mut TraceLogger,
) {
    let pre_hec = state.hec.value();

    // Capture register state prior to execution
    let stcr_list: Vec<StcrState> = (0..32)
        .map(|i| {
            let desc = state.stcr_file.read_descriptor(i);
            StcrState {
                id: i as u8,
                valid: desc.as_ref().is_some_and(|d| d.valid),
                spatial_mask: desc.as_ref().map_or(0, |d| d.spatial_mask),
                base_address: desc.as_ref().map_or(0, |d| d.base_address),
                max_epoch: desc.as_ref().map_or(0, |d| d.max_epoch),
            }
        })
        .collect();

    let opcode_val = match inst.opcode {
        Ok(op) => op as u8,
        Err(code) => code,
    };

    let mut status = "COMMIT".to_string();
    let mut trap_cause_str: Option<String> = None;
    let mut dest_reg_val = 0u64;

    match inst.opcode {
        Ok(Opcode::InvokeCap) => {
            let req_perm = spatial_rights::EXEC;
            let cap_desc = state.stcr_file.read_descriptor(inst.stcr_id as usize);
            match GuardPipeline::evaluate_invoke(cap_desc.as_ref(), req_perm, pre_hec) {
                Ok(()) => {
                    if let Some(ref cap) = cap_desc {
                        state.pc = cap.base_address;
                        dest_reg_val = cap.base_address as u64;
                    }
                }
                Err(cause) => {
                    status = "EFF_TRAP".to_string();
                    trap_cause_str = Some(format!("{:?}", cause));
                    state.trap_flag = true;
                    state.stcr_file.zero_register(inst.stcr_id as usize); // e_val 0 neutral write
                    dest_reg_val = 0;
                }
            }
        }
        Ok(Opcode::HecInc) => {
            let _ = state.hec.increment();
            dest_reg_val = state.hec.value() as u64;
        }
        Ok(Opcode::RestrictCap) => {
            if let Some(mut cap) = state.stcr_file.read_descriptor(inst.stcr_id as usize) {
                cap.spatial_mask &= inst.immediate;
                state
                    .stcr_file
                    .write_descriptor(inst.stcr_id as usize, &cap);
                dest_reg_val = cap.encode();
            }
        }
        Ok(Opcode::RevokeCap) => {
            state.stcr_file.zero_register(inst.stcr_id as usize);
            dest_reg_val = 0;
        }
        Ok(Opcode::GrantCap) => {
            dest_reg_val = 0;
        }
        Err(reserved_code) => {
            status = "EFF_TRAP".to_string();
            trap_cause_str = Some(format!("{:?}", TrapCause::ReservedOpcode(reserved_code)));
            state.trap_flag = true;
            state.stcr_file.zero_register(inst.stcr_id as usize);
            dest_reg_val = 0;
        }
    }

    logger.log_step(StepTraceRecord {
        step_id: step_num,
        pc: state.pc,
        reg_hec: pre_hec,
        stcr_file: stcr_list,
        instruction: InstructionTrace {
            raw_hex: format!("{:#010x}", inst.raw),
            opcode: opcode_val,
        },
        outcome: OutcomeTrace {
            status,
            trap_cause: trap_cause_str,
            dest_reg_val,
        },
    });
}
