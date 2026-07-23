use std::fs::File;
use std::io::Read;
use std::path::Path;
use crate::isa::Instruction;

const MAGIC_CORTEX: &[u8; 6] = b"CORTEX";

#[derive(Debug, PartialEq, Eq)]
pub enum LoadError {
    IoError(String),
    InvalidMagic,
    UnsupportedVersion(u16),
    TruncatedHeader,
    InstructionCountMismatch { expected: usize, actual: usize },
}

impl std::fmt::Display for LoadError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LoadError::IoError(msg) => write!(f, "IO Error: {}", msg),
            LoadError::InvalidMagic => write!(f, "Invalid Magic Header (expected 'CORTEX')"),
            LoadError::UnsupportedVersion(v) => write!(f, "Unsupported Version: {}", v),
            LoadError::TruncatedHeader => write!(f, "Truncated Header (< 12 bytes)"),
            LoadError::InstructionCountMismatch { expected, actual } => {
                write!(f, "Count Mismatch: expected {} bytes payload, got {}", expected, actual)
            }
        }
    }
}

impl std::error::Error for LoadError {}

#[derive(Debug, Clone)]
pub struct Program {
    pub instruction_count: u32,
    pub instructions: Vec<Instruction>,
}

pub fn load_program<P: AsRef<Path>>(path: P) -> Result<Program, LoadError> {
    let mut file = File::open(path).map_err(|e| LoadError::IoError(e.to_string()))?;
    let mut buffer = Vec::new();
    file.read_to_end(&mut buffer).map_err(|e| LoadError::IoError(e.to_string()))?;

    if buffer.len() < 12 {
        return Err(LoadError::TruncatedHeader);
    }

    if &buffer[0..6] != MAGIC_CORTEX {
        return Err(LoadError::InvalidMagic);
    }

    let version = u16::from_be_bytes([buffer[6], buffer[7]]);
    if version != 1 {
        return Err(LoadError::UnsupportedVersion(version));
    }

    let count = u32::from_be_bytes([buffer[8], buffer[9], buffer[10], buffer[11]]) as usize;
    let payload = &buffer[12..];

    if payload.len() != count * 4 {
        return Err(LoadError::InstructionCountMismatch {
            expected: count * 4,
            actual: payload.len(),
        });
    }

    let mut instructions = Vec::with_capacity(count);
    for chunk in payload.chunks_exact(4) {
        let raw_u32 = u32::from_be_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]);
        instructions.push(Instruction::decode(raw_u32));
    }

    Ok(Program {
        instruction_count: count as u32,
        instructions,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_load_truncated_header() {
        let err = load_program("/nonexistent/file.bin");
        assert!(matches!(err, Err(LoadError::IoError(_))));
    }
}
