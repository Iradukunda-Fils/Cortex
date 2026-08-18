//! Conformance tests for Rust Layer 2 Streaming against draft vectors

use cortex_emulator::streaming::{decode_frame, CbeFrameError, FrameType, StreamDecoder};
use std::fs;

#[test]
fn test_valid_st01_single_frame() {
    let data = fs::read("../research/formalization/streaming/valid/st-01-single-frame.cbeframe")
        .expect("Failed to read st-01");
    let frame = decode_frame(&data, Some(0)).expect("Decoding st-01 failed");

    assert_eq!(frame.frame_type, FrameType::Data);
    assert_eq!(frame.sequence, 0);
    assert_eq!(frame.encode(), data);
}

#[test]
fn test_valid_st02_multi_frame() {
    let data = fs::read("../research/formalization/streaming/valid/st-02-multi-frame.cbeframe")
        .expect("Failed to read st-02");
    let mut decoder = StreamDecoder::new(0);
    let frames = decoder.feed(&data).expect("Decoding st-02 failed");

    assert_eq!(frames.len(), 3);
    assert_eq!(frames[0].frame_type, FrameType::Data);
    assert_eq!(frames[0].sequence, 0);
    assert_eq!(frames[1].frame_type, FrameType::Data);
    assert_eq!(frames[1].sequence, 1);
    assert_eq!(frames[2].frame_type, FrameType::End);
    assert_eq!(frames[2].sequence, 2);
}

#[test]
fn test_valid_st03_control_sequence() {
    let data =
        fs::read("../research/formalization/streaming/valid/st-03-control-sequence.cbeframe")
            .expect("Failed to read st-03");
    let mut decoder = StreamDecoder::new(0);
    let frames = decoder.feed(&data).expect("Decoding st-03 failed");

    assert_eq!(frames.len(), 4);
    assert_eq!(frames[0].frame_type, FrameType::Data);
    assert_eq!(frames[1].frame_type, FrameType::Ping);
    assert_eq!(frames[2].frame_type, FrameType::Pong);
    assert_eq!(frames[3].frame_type, FrameType::Data);
}

#[test]
fn test_boundary_st_b01_zero_length_control() {
    let data = fs::read(
        "../research/formalization/streaming/boundaries/st-b01-zero-length-control.cbeframe",
    )
    .expect("Failed to read st-b01");
    let frame = decode_frame(&data, Some(0)).expect("Decoding st-b01 failed");

    assert_eq!(frame.frame_type, FrameType::End);
    assert_eq!(frame.sequence, 0);
    assert!(frame.payload.is_empty());
}

#[test]
fn test_boundary_st_b04_sequence_max() {
    let data =
        fs::read("../research/formalization/streaming/boundaries/st-b04-sequence-max.cbeframe")
            .expect("Failed to read st-b04");
    let frame = decode_frame(&data, Some(u32::MAX)).expect("Decoding st-b04 failed");

    assert_eq!(frame.frame_type, FrameType::Data);
    assert_eq!(frame.sequence, u32::MAX);
}

#[test]
fn test_invalid_st_err01_oversized() {
    let data = fs::read("../research/formalization/streaming/invalid/st-err-01-oversized.cbeframe")
        .expect("Failed to read st-err-01");
    let err = decode_frame(&data, None).unwrap_err();

    assert!(matches!(err, CbeFrameError::FrameTooLarge(_)));
}

#[test]
fn test_invalid_st_err02_truncated_header() {
    let data =
        fs::read("../research/formalization/streaming/invalid/st-err-02-truncated-header.cbeframe")
            .expect("Failed to read st-err-02");
    let err = decode_frame(&data, None).unwrap_err();

    assert!(matches!(err, CbeFrameError::TruncatedHeader(_)));
}

#[test]
fn test_invalid_st_err04_bad_magic() {
    let data = fs::read("../research/formalization/streaming/invalid/st-err-04-bad-magic.cbeframe")
        .expect("Failed to read st-err-04");
    let err = decode_frame(&data, None).unwrap_err();

    assert!(matches!(err, CbeFrameError::MagicMismatch(_)));
}

#[test]
fn test_invalid_st_err05_sequence_gap() {
    let data =
        fs::read("../research/formalization/streaming/invalid/st-err-05-sequence-gap.cbeframe")
            .expect("Failed to read st-err-05");
    let mut decoder = StreamDecoder::new(0);
    let err = decoder.feed(&data).unwrap_err();

    assert!(matches!(err, CbeFrameError::SequenceGap { .. }));
}

#[test]
fn test_invalid_st_err06_sequence_overflow() {
    let data = fs::read(
        "../research/formalization/streaming/invalid/st-err-06-sequence-overflow.cbeframe",
    )
    .expect("Failed to read st-err-06");
    let mut decoder = StreamDecoder::new(u32::MAX);
    let err = decoder.feed(&data).unwrap_err();

    assert!(matches!(err, CbeFrameError::SequenceOverflow));
}
