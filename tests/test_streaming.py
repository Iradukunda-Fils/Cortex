"""
Unit tests for Layer 2 Transport Framing & Streaming (cortex/cbe/streaming.py)
"""

import unittest

from cortex.cbe.streaming import (
    HEADER_SIZE,
    MAX_SEQUENCE,
    CBEDataEmptyError,
    CBEFrameTooLargeError,
    CBEInvalidControlPayloadError,
    CBEMagicMismatchError,
    CBESequenceGapError,
    CBESequenceOverflowError,
    CBETruncatedHeaderError,
    CBETruncatedPayloadError,
    CortexFrame,
    FrameType,
    StreamDecoder,
    StreamEncoder,
    decode_frame,
    encode_frame,
)


class TestCBEStreaming(unittest.TestCase):
    """Tests for Cortex Layer 2 transport framing."""

    def test_single_frame_encode_decode_round_trip(self) -> None:
        payload = b"L4:S6:wf-101S14:payment:chargeS8:caus-999M2:S6:amountI100S8:currencyS3:USD"
        frame = CortexFrame(frame_type=FrameType.DATA, sequence=0, payload=payload)

        encoded = encode_frame(frame)
        self.assertEqual(len(encoded), HEADER_SIZE + len(payload))
        self.assertTrue(encoded.startswith(b"CF\x01\x00\x00\x00\x00"))

        decoded = decode_frame(encoded, expected_sequence=0)
        self.assertEqual(decoded.frame_type, FrameType.DATA)
        self.assertEqual(decoded.sequence, 0)
        self.assertEqual(decoded.payload, payload)
        self.assertEqual(encode_frame(decoded), encoded)

    def test_control_frame_zero_payload_rules(self) -> None:
        for ftype in (FrameType.PING, FrameType.PONG, FrameType.END):
            frame = CortexFrame(frame_type=ftype, sequence=1, payload=b"")
            encoded = encode_frame(frame)
            decoded = decode_frame(encoded, expected_sequence=1)
            self.assertEqual(decoded.frame_type, ftype)
            self.assertEqual(len(decoded.payload), 0)

            with self.assertRaises(CBEInvalidControlPayloadError):
                CortexFrame(frame_type=ftype, sequence=1, payload=b"invalid")

    def test_error_control_frame_four_byte_payload(self) -> None:
        err_code_bytes = (0x2001).to_bytes(4, "big")
        frame = CortexFrame(frame_type=FrameType.ERROR, sequence=2, payload=err_code_bytes)
        encoded = encode_frame(frame)
        decoded = decode_frame(encoded, expected_sequence=2)
        self.assertEqual(decoded.frame_type, FrameType.ERROR)
        self.assertEqual(decoded.payload, err_code_bytes)

        with self.assertRaises(CBEInvalidControlPayloadError):
            CortexFrame(frame_type=FrameType.ERROR, sequence=2, payload=b"")

    def test_data_frame_empty_payload_rejection(self) -> None:
        with self.assertRaises(CBEDataEmptyError):
            CortexFrame(frame_type=FrameType.DATA, sequence=0, payload=b"")

    def test_stateful_stream_encoder_decoder_session(self) -> None:
        encoder = StreamEncoder(initial_sequence=0)
        decoder = StreamDecoder(expected_sequence=0)

        chunk1 = encoder.encode(FrameType.DATA, b"L1:S5:hello")
        chunk2 = encoder.encode(FrameType.PING)
        chunk3 = encoder.encode(FrameType.PONG)
        chunk4 = encoder.encode(FrameType.END)

        stream = chunk1 + chunk2 + chunk3 + chunk4
        frames = decoder.feed(stream)

        self.assertEqual(len(frames), 4)
        self.assertEqual(frames[0].frame_type, FrameType.DATA)
        self.assertEqual(frames[0].sequence, 0)
        self.assertEqual(frames[1].frame_type, FrameType.PING)
        self.assertEqual(frames[1].sequence, 1)
        self.assertEqual(frames[2].frame_type, FrameType.PONG)
        self.assertEqual(frames[2].sequence, 2)
        self.assertEqual(frames[3].frame_type, FrameType.END)
        self.assertEqual(frames[3].sequence, 3)

    def test_sequence_gap_rejection(self) -> None:
        encoder = StreamEncoder(initial_sequence=0)
        decoder = StreamDecoder(expected_sequence=0)

        f0 = encoder.encode(FrameType.DATA, b"payload1")
        f1 = encoder.encode(FrameType.DATA, b"payload2")

        decoder.feed(f0)
        # Manually alter sequence in second frame
        bad_f1 = f1[:3] + (5).to_bytes(4, "big") + f1[7:]
        with self.assertRaises(CBESequenceGapError):
            decoder.feed(bad_f1)

    def test_sequence_overflow_rejection(self) -> None:
        encoder = StreamEncoder(initial_sequence=MAX_SEQUENCE)
        frame1 = encoder.encode(FrameType.DATA, b"max_seq_frame")
        self.assertTrue(len(frame1) > 0)

        with self.assertRaises(CBESequenceOverflowError):
            encoder.encode(FrameType.DATA, b"overflow_frame")

    def test_magic_mismatch_rejection(self) -> None:
        bad_data = b"XY\x01\x00\x00\x00\x00\x00\x00\x00\x04test"
        with self.assertRaises(CBEMagicMismatchError):
            decode_frame(bad_data)

    def test_oversized_frame_rejection(self) -> None:
        # Header length 17,000,000 > 16MiB
        hdr = b"CF\x01\x00\x00\x00\x00\x01\x03\x79\x00"
        with self.assertRaises(CBEFrameTooLargeError):
            decode_frame(hdr)

    def test_truncated_header_rejection(self) -> None:
        with self.assertRaises(CBETruncatedHeaderError):
            decode_frame(b"CF\x01\x00\x00")

    def test_truncated_payload_rejection(self) -> None:
        # Header len 10, but payload is 4 bytes
        hdr = b"CF\x01\x00\x00\x00\x00\x00\x00\x00\x0A1234"
        with self.assertRaises(CBETruncatedPayloadError):
            decode_frame(hdr)


if __name__ == "__main__":
    unittest.main()
