use serde::{Deserialize, Serialize};

/// 64-bit Spatiotemporal Capability Register (STCR) descriptor (SDS v1.0 Section 3).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct CapabilityDescriptor {
    pub valid: bool,
    pub spatial_mask: u16, // 15 bits used (bits 62..48)
    pub base_address: u32, // 32 bits (bits 47..16)
    pub max_epoch: u16,    // 16 bits (bits 15..0)
}

/// Bit constants for Spatial_Mask enumeration (SDS v1.0 Section 3.1)
#[allow(dead_code)]
pub mod spatial_rights {
    pub const READ: u16 = 1 << 14;     // Bit 62
    pub const WRITE: u16 = 1 << 13;    // Bit 61
    pub const EXEC: u16 = 1 << 12;     // Bit 60
    pub const DELEGATE: u16 = 1 << 11; // Bit 59
    pub const REVOKE: u16 = 1 << 10;   // Bit 58
    pub const DOMAIN_MASK: u16 = 0x03FF; // Bits 57..48 (10 bits)
}

impl CapabilityDescriptor {
    pub fn new(valid: bool, spatial_mask: u16, base_address: u32, max_epoch: u16) -> Self {
        Self {
            valid,
            spatial_mask: spatial_mask & 0x7FFF,
            base_address,
            max_epoch,
        }
    }

    /// Executable encoding function encode(c) -> u64 (SDS v1.0 Section 6.1)
    pub fn encode(&self) -> u64 {
        if !self.valid {
            return 0;
        }
        let v_bit = 1u64 << 63;
        let mask_bits = ((self.spatial_mask & 0x7FFF) as u64) << 48;
        let addr_bits = (self.base_address as u64) << 16;
        let epoch_bits = (self.max_epoch & 0xFFFF) as u64;

        v_bit | mask_bits | addr_bits | epoch_bits
    }

    /// Executable decoding function decode(R) -> Option<CapabilityDescriptor> (SDS v1.0 Section 6.1)
    pub fn decode(raw: u64) -> Option<Self> {
        let valid = (raw >> 63) == 1;
        if !valid {
            return None;
        }
        Some(Self {
            valid: true,
            spatial_mask: ((raw >> 48) & 0x7FFF) as u16,
            base_address: ((raw >> 16) & 0xFFFFFFFF) as u32,
            max_epoch: (raw & 0xFFFF) as u16,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encode_decode_roundtrip() {
        let cap = CapabilityDescriptor::new(true, spatial_rights::READ | spatial_rights::EXEC, 0x00001000, 42);
        let encoded = cap.encode();
        let decoded = CapabilityDescriptor::decode(encoded).expect("Decode failed");
        assert_eq!(cap, decoded);
    }

    #[test]
    fn test_invalid_cap_decodes_to_none() {
        let raw = 0u64; // V bit cleared
        assert_eq!(CapabilityDescriptor::decode(raw), None);
    }
}
