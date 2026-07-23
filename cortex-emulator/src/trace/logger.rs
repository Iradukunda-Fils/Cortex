use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StcrState {
    pub id: u8,
    pub valid: bool,
    pub spatial_mask: u16,
    pub base_address: u32,
    pub max_epoch: u16,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstructionTrace {
    pub raw_hex: String,
    pub opcode: u8,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutcomeTrace {
    pub status: String, // "COMMIT" or "EFF_TRAP"
    pub trap_cause: Option<String>,
    pub dest_reg_val: u64,
}

/// Standardized execution step matching trace_schema.json
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StepTraceRecord {
    pub step_id: usize,
    pub pc: u32,
    pub reg_hec: u16,
    pub stcr_file: Vec<StcrState>,
    pub instruction: InstructionTrace,
    pub outcome: OutcomeTrace,
}

#[derive(Debug, Default)]
pub struct TraceLogger {
    records: Vec<StepTraceRecord>,
}

impl TraceLogger {
    pub fn new() -> Self {
        Self { records: Vec::new() }
    }

    pub fn log_step(&mut self, record: StepTraceRecord) {
        self.records.push(record);
    }

    pub fn to_json_string(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string_pretty(&self.records)
    }

    #[allow(dead_code)]
    pub fn records(&self) -> &[StepTraceRecord] {
        &self.records
    }
}
