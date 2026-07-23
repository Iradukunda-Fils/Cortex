use serde::{Deserialize, Serialize};

/// Fixed 32-bit STCR ISA Opcode space (SDS v1.0 Section 4.2)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[repr(u8)]
pub enum Opcode {
    InvokeCap = 0x01,
    GrantCap = 0x02,
    RestrictCap = 0x03,
    RevokeCap = 0x04,
    HecInc = 0x05,
}

impl TryFrom<u8> for Opcode {
    type Error = u8;

    fn try_from(value: u8) -> Result<Self, Self::Error> {
        match value {
            0x01 => Ok(Opcode::InvokeCap),
            0x02 => Ok(Opcode::GrantCap),
            0x03 => Ok(Opcode::RestrictCap),
            0x04 => Ok(Opcode::RevokeCap),
            0x05 => Ok(Opcode::HecInc),
            other => Err(other),
        }
    }
}

/// Decoded 32-bit STCR Instruction format (SDS v1.0 Section 4.1)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Instruction {
    pub raw: u32,
    pub opcode: Result<Opcode, u8>, // Reserved opcodes returned as Err(raw_opcode)
    pub stcr_id: u8,               // 5 bits (bits 25..21)
    pub arg_reg: u8,               // 5 bits (bits 20..16)
    pub immediate: u16,            // 16 bits (bits 15..0)
}

impl Instruction {
    pub fn decode(raw: u32) -> Self {
        let opcode_raw = ((raw >> 26) & 0x3F) as u8;
        let stcr_id = ((raw >> 21) & 0x1F) as u8;
        let arg_reg = ((raw >> 16) & 0x1F) as u8;
        let immediate = (raw & 0xFFFF) as u16;

        Self {
            raw,
            opcode: Opcode::try_from(opcode_raw),
            stcr_id,
            arg_reg,
            immediate,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_instruction_decode_valid() {
        // Opcode 0x01 (invoke_cap), STCR_ID 1, Arg_Reg 3, Immediate 0x0001
        let raw = (0x01u32 << 26) | (1u32 << 21) | (3u32 << 16) | 0x0001;
        let inst = Instruction::decode(raw);
        assert_eq!(inst.opcode, Ok(Opcode::InvokeCap));
        assert_eq!(inst.stcr_id, 1);
        assert_eq!(inst.arg_reg, 3);
        assert_eq!(inst.immediate, 0x0001);
    }

    #[test]
    fn test_instruction_decode_reserved_opcode() {
        // Opcode 0x3F (Reserved)
        let raw = 0x3Fu32 << 26;
        let inst = Instruction::decode(raw);
        assert_eq!(inst.opcode, Err(0x3F));
    }
}
