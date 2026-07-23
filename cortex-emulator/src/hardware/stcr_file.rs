use crate::isa::CapabilityDescriptor;
use serde::{Deserialize, Serialize};

pub const NUM_STCR_REGISTERS: usize = 32;

/// 32-entry STCR Register File (SDS v1.0 Section 3)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StcrFile {
    registers: [u64; NUM_STCR_REGISTERS],
}

impl Default for StcrFile {
    fn default() -> Self {
        Self::new()
    }
}

impl StcrFile {
    pub fn new() -> Self {
        Self {
            registers: [0u64; NUM_STCR_REGISTERS],
        }
    }

    pub fn read_raw(&self, index: usize) -> u64 {
        if index < NUM_STCR_REGISTERS {
            self.registers[index]
        } else {
            0
        }
    }

    pub fn read_descriptor(&self, index: usize) -> Option<CapabilityDescriptor> {
        let raw = self.read_raw(index);
        CapabilityDescriptor::decode(raw)
    }

    pub fn write_raw(&mut self, index: usize, val: u64) {
        if index < NUM_STCR_REGISTERS {
            self.registers[index] = val;
        }
    }

    pub fn write_descriptor(&mut self, index: usize, cap: &CapabilityDescriptor) {
        self.write_raw(index, cap.encode());
    }

    /// Zero out a destination register on trap (SDS v1.0 Section 5.1 e_val 0)
    pub fn zero_register(&mut self, index: usize) {
        self.write_raw(index, 0);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::isa::spatial_rights;

    #[test]
    fn test_stcr_read_write() {
        let mut file = StcrFile::new();
        let cap = CapabilityDescriptor::new(true, spatial_rights::READ, 0x1000, 10);
        file.write_descriptor(1, &cap);
        assert_eq!(file.read_descriptor(1), Some(cap));

        file.zero_register(1);
        assert_eq!(file.read_descriptor(1), None);
    }
}
