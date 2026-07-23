use crate::hardware::TrapCause;
use crate::isa::CapabilityDescriptor;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct PreState {
    pub reg_hec: u16,
    pub stcr_raw: String,
    pub stcr_decoded: Option<CapabilityDescriptor>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PostState {
    pub pc: String,
    pub trap_flag: bool,
    pub trap_cause: Option<TrapCause>,
}

/// Structured JSON Execution Trace Record matching step_m operational reductions
#[derive(Debug, Serialize, Deserialize)]
pub struct StepTraceRecord {
    pub step: u64,
    pub instruction: String,
    pub pre_state: PreState,
    pub guard_result: String, // "PASS" or "TRAP"
    pub post_state: PostState,
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
