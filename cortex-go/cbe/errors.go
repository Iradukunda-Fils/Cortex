/*
Package cbe implements the Cortex Canonical Byte Encoding (CBE) protocol kernel.

This file defines the deterministic error taxonomy for CBE encoding and decoding
failures, mirroring the Revision #5 fault domain specification.
*/
package cbe

import "fmt"

// CBEError is the base error type for all CBE protocol violations.
type CBEError struct {
	Code    string
	Message string
}

func (e *CBEError) Error() string {
	return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

// Sentinel error codes matching the Revision #5 fault domain specification.
const (
	CodeInvalidUTF8     = "CBE_INVALID_UTF8"
	CodeNonNFC          = "CBE_NON_NFC"
	CodeDuplicateKey    = "CBE_DUPLICATE_KEY"
	CodeNonCanonicalMap = "CBE_NON_CANONICAL_MAP"
	CodeIntOverflow     = "CBE_INT_OVERFLOW"
	CodeFloatNonFinite  = "CBE_FLOAT_NONFINITE"
	CodeInvalidLength   = "CBE_INVALID_LENGTH"
	CodeUnknownTag      = "CBE_UNKNOWN_TAG"
)

func errInvalidUTF8(msg string) error {
	return &CBEError{Code: CodeInvalidUTF8, Message: msg}
}

func errNonNFC(msg string) error {
	return &CBEError{Code: CodeNonNFC, Message: msg}
}

func errDuplicateKey(msg string) error {
	return &CBEError{Code: CodeDuplicateKey, Message: msg}
}

func errNonCanonicalMap(msg string) error {
	return &CBEError{Code: CodeNonCanonicalMap, Message: msg}
}

func errIntOverflow(msg string) error {
	return &CBEError{Code: CodeIntOverflow, Message: msg}
}

func errFloatNonFinite(msg string) error {
	return &CBEError{Code: CodeFloatNonFinite, Message: msg}
}

func errInvalidLength(msg string) error {
	return &CBEError{Code: CodeInvalidLength, Message: msg}
}

func errUnknownTag(msg string) error {
	return &CBEError{Code: CodeUnknownTag, Message: msg}
}

// ErrorCode extracts the CBE error code from an error, if it is a *CBEError.
func ErrorCode(err error) string {
	if cbeErr, ok := err.(*CBEError); ok {
		return cbeErr.Code
	}
	return ""
}
