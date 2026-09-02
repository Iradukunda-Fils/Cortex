//! Cortex Layer 2 Transport Framing & Streaming Module (Rust Engine)

use std::convert::TryFrom;

pub const MAGIC_BYTES: &[u8; 2] = b"CF";
pub const HEADER_SIZE: usize = 11;
pub const MAX_FRAME_SIZE: usize = 16_777_216; // 16 MiB
pub const MAX_SEQUENCE: u32 = u32::MAX;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum FrameType {
    Data = 0x01,
    Ping = 0x02,
    Pong = 0x03,
    End = 0x04,
    Error = 0xFF,
}

impl TryFrom<u8> for FrameType {
    type Error = CbeFrameError;

    fn try_from(value: u8) -> Result<Self, CbeFrameError> {
        match value {
            0x01 => Ok(FrameType::Data),
            0x02 => Ok(FrameType::Ping),
            0x03 => Ok(FrameType::Pong),
            0x04 => Ok(FrameType::End),
            0xFF => Ok(FrameType::Error),
            other => Err(CbeFrameError::UnknownType(other)),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CbeFrameError {
    MagicMismatch([u8; 2]),
    UnknownType(u8),
    FrameTooLarge(usize),
    SequenceGap { expected: u32, got: u32 },
    SequenceOverflow,
    TruncatedHeader(usize),
    TruncatedPayload { expected: usize, got: usize },
    InvalidControlPayload { frame_type: FrameType, len: usize },
    DataEmpty,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CortexFrame {
    pub frame_type: FrameType,
    pub sequence: u32,
    pub payload: Vec<u8>,
}

impl CortexFrame {
    pub fn new(
        frame_type: FrameType,
        sequence: u32,
        payload: Vec<u8>,
    ) -> Result<Self, CbeFrameError> {
        if payload.len() > MAX_FRAME_SIZE {
            return Err(CbeFrameError::FrameTooLarge(payload.len()));
        }

        match frame_type {
            FrameType::Ping | FrameType::Pong | FrameType::End => {
                if !payload.is_empty() {
                    return Err(CbeFrameError::InvalidControlPayload {
                        frame_type,
                        len: payload.len(),
                    });
                }
            }
            FrameType::Error => {
                if payload.len() != 4 {
                    return Err(CbeFrameError::InvalidControlPayload {
                        frame_type,
                        len: payload.len(),
                    });
                }
            }
            FrameType::Data => {
                if payload.is_empty() {
                    return Err(CbeFrameError::DataEmpty);
                }
            }
        }

        Ok(CortexFrame {
            frame_type,
            sequence,
            payload,
        })
    }

    pub fn encode(&self) -> Vec<u8> {
        let payload_len = u32::try_from(self.payload.len()).unwrap_or(u32::MAX);
        let mut bytes = Vec::with_capacity(HEADER_SIZE + self.payload.len());
        bytes.extend_from_slice(MAGIC_BYTES);
        bytes.push(self.frame_type as u8);
        bytes.extend_from_slice(&self.sequence.to_be_bytes());
        bytes.extend_from_slice(&payload_len.to_be_bytes());
        bytes.extend_from_slice(&self.payload);
        bytes
    }
}

pub fn decode_frame(
    data: &[u8],
    expected_sequence: Option<u32>,
) -> Result<CortexFrame, CbeFrameError> {
    if data.len() < HEADER_SIZE {
        return Err(CbeFrameError::TruncatedHeader(data.len()));
    }

    let magic_bytes = data.get(0..2).ok_or(CbeFrameError::TruncatedHeader(data.len()))?;
    let magic: [u8; 2] = magic_bytes.try_into().unwrap();
    if magic != *MAGIC_BYTES {
        return Err(CbeFrameError::MagicMismatch(magic));
    }

    let tag_byte = data.get(2).ok_or(CbeFrameError::TruncatedHeader(data.len()))?;
    let frame_type = FrameType::try_from(*tag_byte)?;

    let seq_bytes = data.get(3..7).ok_or(CbeFrameError::TruncatedHeader(data.len()))?;
    let sequence = u32::from_be_bytes(seq_bytes.try_into().unwrap());

    let len_bytes = data.get(7..11).ok_or(CbeFrameError::TruncatedHeader(data.len()))?;
    let payload_len = u32::from_be_bytes(len_bytes.try_into().unwrap()) as usize;




    if let Some(expected) = expected_sequence {
        if sequence != expected {
            return Err(CbeFrameError::SequenceGap {
                expected,
                got: sequence,
            });
        }
    }

    // Allocation protection check BEFORE buffer allocation
    if payload_len > MAX_FRAME_SIZE {
        return Err(CbeFrameError::FrameTooLarge(payload_len));
    }

    let payload_slice = data
        .get(HEADER_SIZE..)
        .ok_or(CbeFrameError::TruncatedHeader(data.len()))?;

    if payload_slice.len() < payload_len {
        return Err(CbeFrameError::TruncatedPayload {
            expected: payload_len,
            got: payload_slice.len(),
        });
    }

    let payload = payload_slice
        .get(..payload_len)
        .ok_or(CbeFrameError::TruncatedPayload {
            expected: payload_len,
            got: payload_slice.len(),
        })?
        .to_vec();

    CortexFrame::new(frame_type, sequence, payload)

}

pub struct StreamEncoder {
    next_sequence: Option<u32>,
}

impl StreamEncoder {
    pub fn new(initial_sequence: u32) -> Self {
        StreamEncoder {
            next_sequence: Some(initial_sequence),
        }
    }

    pub fn encode(
        &mut self,
        frame_type: FrameType,
        payload: Vec<u8>,
    ) -> Result<Vec<u8>, CbeFrameError> {
        let seq = self.next_sequence.ok_or(CbeFrameError::SequenceOverflow)?;
        let frame = CortexFrame::new(frame_type, seq, payload)?;
        let encoded = frame.encode();

        if seq == MAX_SEQUENCE {
            self.next_sequence = None; // Trigger overflow error on next invocation
        } else {
            self.next_sequence = Some(seq + 1);
        }

        Ok(encoded)
    }
}

pub struct StreamDecoder {
    expected_sequence: Option<u32>,
    buffer: Vec<u8>,
}

impl StreamDecoder {
    pub fn new(initial_sequence: u32) -> Self {
        StreamDecoder {
            expected_sequence: Some(initial_sequence),
            buffer: Vec::new(),
        }
    }

    pub fn feed(&mut self, chunk: &[u8]) -> Result<Vec<CortexFrame>, CbeFrameError> {
        self.buffer.extend_from_slice(chunk);
        let mut frames = Vec::new();
        while self.buffer.len() >= HEADER_SIZE {


            let magic_bytes = self.buffer.get(0..2).ok_or(CbeFrameError::TruncatedHeader(self.buffer.len()))?;

            let magic: [u8; 2] = magic_bytes.try_into().unwrap();
            if magic != *MAGIC_BYTES {
                return Err(CbeFrameError::MagicMismatch(magic));
            }

            let tag_byte = self.buffer.get(2).ok_or(CbeFrameError::TruncatedHeader(self.buffer.len()))?;
            let _frame_type = FrameType::try_from(*tag_byte)?;

            let seq_bytes = self.buffer.get(3..7).ok_or(CbeFrameError::TruncatedHeader(self.buffer.len()))?;
            let sequence = u32::from_be_bytes(seq_bytes.try_into().unwrap());

            let len_bytes = self.buffer.get(7..11).ok_or(CbeFrameError::TruncatedHeader(self.buffer.len()))?;
            let payload_len = u32::from_be_bytes(len_bytes.try_into().unwrap()) as usize;




            // Allocation protection check BEFORE buffer allocation
            if payload_len > MAX_FRAME_SIZE {
                return Err(CbeFrameError::FrameTooLarge(payload_len));
            }

            let total_len = HEADER_SIZE + payload_len;
            if self.buffer.len() < total_len {
                break; // Await more payload bytes
            }

            let expected_seq = self
                .expected_sequence
                .ok_or(CbeFrameError::SequenceOverflow)?;
            if sequence != expected_seq {
                return Err(CbeFrameError::SequenceGap {
                    expected: expected_seq,
                    got: sequence,
                });
            }

            let frame_bytes: Vec<u8> = self.buffer.drain(..total_len).collect();
            let frame = decode_frame(&frame_bytes, Some(expected_seq))?;
            frames.push(frame);

            if expected_seq == MAX_SEQUENCE {
                self.expected_sequence = None;
            } else {
                self.expected_sequence = Some(expected_seq + 1);
            }
        }

        Ok(frames)
    }
}
