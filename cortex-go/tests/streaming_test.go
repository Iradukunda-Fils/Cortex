package tests

import (
	"errors"
	"os"
	"path/filepath"
	"testing"

	"cortex-go/cbe"
)

func getVectorPath(rel string) string {
	return filepath.Join("..", "..", "research", "formalization", "streaming", rel)
}

func TestValidSt01SingleFrame(t *testing.T) {
	path := getVectorPath(filepath.Join("valid", "st-01-single-frame.cbeframe"))
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("Failed to read vector: %v", err)
	}

	seqZero := uint32(0)
	frame, err := cbe.DecodeFrame(data, &seqZero)
	if err != nil {
		t.Fatalf("Failed to decode st-01: %v", err)
	}

	if frame.Type != cbe.FrameData {
		t.Errorf("Expected FrameData, got %v", frame.Type)
	}
	if frame.Sequence != 0 {
		t.Errorf("Expected sequence 0, got %d", frame.Sequence)
	}

	encoded, err := cbe.EncodeFrame(frame)
	if err != nil {
		t.Fatalf("Failed to re-encode frame: %v", err)
	}
	if string(encoded) != string(data) {
		t.Errorf("Round-trip encoding mismatch")
	}
}

func TestValidSt02MultiFrame(t *testing.T) {
	path := getVectorPath(filepath.Join("valid", "st-02-multi-frame.cbeframe"))
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("Failed to read vector: %v", err)
	}

	decoder := cbe.NewStreamDecoder(0)
	frames, err := decoder.Feed(data)
	if err != nil {
		t.Fatalf("Failed to feed multi-frame stream: %v", err)
	}

	if len(frames) != 3 {
		t.Fatalf("Expected 3 frames, got %d", len(frames))
	}
	if frames[0].Type != cbe.FrameData || frames[0].Sequence != 0 {
		t.Errorf("Frame 0 mismatch")
	}
	if frames[1].Type != cbe.FrameData || frames[1].Sequence != 1 {
		t.Errorf("Frame 1 mismatch")
	}
	if frames[2].Type != cbe.FrameEnd || frames[2].Sequence != 2 {
		t.Errorf("Frame 2 mismatch")
	}
}

func TestValidSt03ControlSequence(t *testing.T) {
	path := getVectorPath(filepath.Join("valid", "st-03-control-sequence.cbeframe"))
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("Failed to read vector: %v", err)
	}

	decoder := cbe.NewStreamDecoder(0)
	frames, err := decoder.Feed(data)
	if err != nil {
		t.Fatalf("Failed to feed control sequence: %v", err)
	}

	if len(frames) != 4 {
		t.Fatalf("Expected 4 frames, got %d", len(frames))
	}
	if frames[0].Type != cbe.FrameData || frames[1].Type != cbe.FramePing ||
		frames[2].Type != cbe.FramePong || frames[3].Type != cbe.FrameData {
		t.Errorf("Control sequence frame types mismatch")
	}
}

func TestBoundaryStB01ZeroLengthControl(t *testing.T) {
	path := getVectorPath(filepath.Join("boundaries", "st-b01-zero-length-control.cbeframe"))
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("Failed to read vector: %v", err)
	}

	seqZero := uint32(0)
	frame, err := cbe.DecodeFrame(data, &seqZero)
	if err != nil {
		t.Fatalf("Failed to decode st-b01: %v", err)
	}

	if frame.Type != cbe.FrameEnd || len(frame.Payload) != 0 {
		t.Errorf("Expected zero-length END frame")
	}
}

func TestInvalidStErr01Oversized(t *testing.T) {
	path := getVectorPath(filepath.Join("invalid", "st-err-01-oversized.cbeframe"))
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("Failed to read vector: %v", err)
	}

	_, err = cbe.DecodeFrame(data, nil)
	if !errors.Is(err, cbe.ErrFrameTooLarge) {
		t.Errorf("Expected ErrFrameTooLarge, got %v", err)
	}
}

func TestInvalidStErr02TruncatedHeader(t *testing.T) {
	path := getVectorPath(filepath.Join("invalid", "st-err-02-truncated-header.cbeframe"))
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("Failed to read vector: %v", err)
	}

	_, err = cbe.DecodeFrame(data, nil)
	if !errors.Is(err, cbe.ErrTruncatedHeader) {
		t.Errorf("Expected ErrTruncatedHeader, got %v", err)
	}
}

func TestInvalidStErr04BadMagic(t *testing.T) {
	path := getVectorPath(filepath.Join("invalid", "st-err-04-bad-magic.cbeframe"))
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("Failed to read vector: %v", err)
	}

	_, err = cbe.DecodeFrame(data, nil)
	if !errors.Is(err, cbe.ErrMagicMismatch) {
		t.Errorf("Expected ErrMagicMismatch, got %v", err)
	}
}

func TestInvalidStErr05SequenceGap(t *testing.T) {
	path := getVectorPath(filepath.Join("invalid", "st-err-05-sequence-gap.cbeframe"))
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("Failed to read vector: %v", err)
	}

	decoder := cbe.NewStreamDecoder(0)
	_, err = decoder.Feed(data)
	if !errors.Is(err, cbe.ErrSequenceGap) {
		t.Errorf("Expected ErrSequenceGap, got %v", err)
	}
}

func TestInvalidStErr06SequenceOverflow(t *testing.T) {
	path := getVectorPath(filepath.Join("invalid", "st-err-06-sequence-overflow.cbeframe"))
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("Failed to read vector: %v", err)
	}

	decoder := cbe.NewStreamDecoder(cbe.MaxSequence)
	_, err = decoder.Feed(data)
	if !errors.Is(err, cbe.ErrSequenceOverflow) {
		t.Errorf("Expected ErrSequenceOverflow, got %v", err)
	}
}
