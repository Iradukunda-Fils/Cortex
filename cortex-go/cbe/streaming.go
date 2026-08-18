// Package cbe implements Cortex Canonical Byte Encoding (CBE) and Layer 2 Transport Framing.
package cbe

import (
	"bytes"
	"encoding/binary"
	"errors"
	"fmt"
)

const (
	HeaderSize   = 11
	MaxFrameSize = 16777216 // 16 MiB
	MaxSequence  = 4294967295 // UINT32_MAX
)

var MagicBytes = []byte{'C', 'F'}

type FrameType byte

const (
	FrameData  FrameType = 0x01
	FramePing  FrameType = 0x02
	FramePong  FrameType = 0x03
	FrameEnd   FrameType = 0x04
	FrameError FrameType = 0xFF
)

var (
	ErrMagicMismatch          = errors.New("CBE_FRAME_MAGIC_MISMATCH")
	ErrUnknownFrameType       = errors.New("CBE_FRAME_UNKNOWN_TYPE")
	ErrFrameTooLarge          = errors.New("CBE_FRAME_TOO_LARGE")
	ErrSequenceGap            = errors.New("CBE_FRAME_SEQUENCE_GAP")
	ErrSequenceOverflow       = errors.New("CBE_FRAME_SEQUENCE_OVERFLOW")
	ErrTruncatedHeader        = errors.New("CBE_FRAME_TRUNCATED_HEADER")
	ErrTruncatedPayload       = errors.New("CBE_FRAME_TRUNCATED_PAYLOAD")
	ErrInvalidControlPayload  = errors.New("CBE_FRAME_INVALID_CONTROL_PAYLOAD")
	ErrDataEmpty              = errors.New("CBE_FRAME_DATA_EMPTY")
)

type CortexFrame struct {
	Type     FrameType
	Sequence uint32
	Payload  []byte
}

func NewCortexFrame(frameType FrameType, sequence uint32, payload []byte) (CortexFrame, error) {
	if len(payload) > MaxFrameSize {
		return CortexFrame{}, ErrFrameTooLarge
	}

	switch frameType {
	case FrameData:
		if len(payload) == 0 {
			return CortexFrame{}, ErrDataEmpty
		}
	case FramePing, FramePong, FrameEnd:
		if len(payload) != 0 {
			return CortexFrame{}, ErrInvalidControlPayload
		}
	case FrameError:
		if len(payload) != 4 {
			return CortexFrame{}, ErrInvalidControlPayload
		}
	default:
		return CortexFrame{}, ErrUnknownFrameType
	}

	return CortexFrame{
		Type:     frameType,
		Sequence: sequence,
		Payload:  payload,
	}, nil
}

func EncodeFrame(frame CortexFrame) ([]byte, error) {
	buf := make([]byte, HeaderSize+len(frame.Payload))
	copy(buf[0:2], MagicBytes)
	buf[2] = byte(frame.Type)
	binary.BigEndian.PutUint32(buf[3:7], frame.Sequence)
	binary.BigEndian.PutUint32(buf[7:11], uint32(len(frame.Payload)))
	copy(buf[11:], frame.Payload)
	return buf, nil
}

func DecodeFrame(data []byte, expectedSequence *uint32) (CortexFrame, error) {
	if len(data) < HeaderSize {
		return CortexFrame{}, ErrTruncatedHeader
	}

	if !bytes.Equal(data[0:2], MagicBytes) {
		return CortexFrame{}, ErrMagicMismatch
	}

	frameType := FrameType(data[2])
	sequence := binary.BigEndian.Uint32(data[3:7])
	payloadLen := int(binary.BigEndian.Uint32(data[7:11]))

	if expectedSequence != nil && sequence != *expectedSequence {
		return CortexFrame{}, fmt.Errorf("%w: expected %d, got %d", ErrSequenceGap, *expectedSequence, sequence)
	}

	// Allocation protection check BEFORE buffer allocation
	if payloadLen > MaxFrameSize {
		return CortexFrame{}, ErrFrameTooLarge
	}

	payloadSlice := data[HeaderSize:]
	if len(payloadSlice) < payloadLen {
		return CortexFrame{}, ErrTruncatedPayload
	}

	payload := make([]byte, payloadLen)
	copy(payload, payloadSlice[:payloadLen])

	return NewCortexFrame(frameType, sequence, payload)
}

type StreamEncoder struct {
	nextSequence uint64 // Used uint64 to track overflow past uint32 max
}

func NewStreamEncoder(initialSequence uint32) *StreamEncoder {
	return &StreamEncoder{
		nextSequence: uint64(initialSequence),
	}
}

func (e *StreamEncoder) Encode(frameType FrameType, payload []byte) ([]byte, error) {
	if e.nextSequence > MaxSequence {
		return nil, ErrSequenceOverflow
	}

	seq := uint32(e.nextSequence)
	frame, err := NewCortexFrame(frameType, seq, payload)
	if err != nil {
		return nil, err
	}

	encoded, err := EncodeFrame(frame)
	if err != nil {
		return nil, err
	}

	e.nextSequence++
	return encoded, nil
}

type StreamDecoder struct {
	expectedSequence uint64
	buffer           []byte
}

func NewStreamDecoder(initialSequence uint32) *StreamDecoder {
	return &StreamDecoder{
		expectedSequence: uint64(initialSequence),
		buffer:           make([]byte, 0),
	}
}

func (d *StreamDecoder) Feed(chunk []byte) ([]CortexFrame, error) {
	d.buffer = append(d.buffer, chunk...)
	frames := make([]CortexFrame, 0)

	for len(d.buffer) >= HeaderSize {
		if !bytes.Equal(d.buffer[0:2], MagicBytes) {
			return nil, ErrMagicMismatch
		}

		sequence := binary.BigEndian.Uint32(d.buffer[3:7])
		payloadLen := int(binary.BigEndian.Uint32(d.buffer[7:11]))

		// Allocation protection check BEFORE buffer allocation
		if payloadLen > MaxFrameSize {
			return nil, ErrFrameTooLarge
		}

		totalLen := HeaderSize + payloadLen
		if len(d.buffer) < totalLen {
			break // Await more payload bytes
		}

		if d.expectedSequence > MaxSequence {
			return nil, ErrSequenceOverflow
		}

		expectedSeq := uint32(d.expectedSequence)
		if sequence != expectedSeq {
			return nil, fmt.Errorf("%w: expected %d, got %d", ErrSequenceGap, expectedSeq, sequence)
		}

		frameBytes := d.buffer[:totalLen]
		frame, err := DecodeFrame(frameBytes, &expectedSeq)
		if err != nil {
			return nil, err
		}

		frames = append(frames, frame)
		d.buffer = d.buffer[totalLen:]
		d.expectedSequence++
	}

	return frames, nil
}
