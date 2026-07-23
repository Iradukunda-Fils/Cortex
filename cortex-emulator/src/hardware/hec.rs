use serde::{Deserialize, Serialize};

/// 16-bit Monotonic Hardware Epoch Counter (REG_HEC) (SDS v1.0 Section 5)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct HardwareEpochCounter {
    value: u16,
}

impl Default for HardwareEpochCounter {
    fn default() -> Self {
        Self::new()
    }
}

impl HardwareEpochCounter {
    pub fn new() -> Self {
        Self { value: 0 }
    }

    pub fn value(&self) -> u16 {
        self.value
    }

    /// Privileged monotonic increment (hec.inc)
    pub fn increment(&mut self) -> Result<u16, &'static str> {
        if self.value == u16::MAX {
            Err("HEC Overflow: Epoch counter reached 0xFFFF limit")
        } else {
            self.value += 1;
            Ok(self.value)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hec_monotonic_increment() {
        let mut hec = HardwareEpochCounter::new();
        assert_eq!(hec.value(), 0);
        assert_eq!(hec.increment(), Ok(1));
        assert_eq!(hec.value(), 1);
    }
}
