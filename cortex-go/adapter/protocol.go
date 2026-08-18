/*
Protocol adapter exposing the 4 stateless CBE primitives for Gate E evaluation:
  1. EncodeCBE(value) -> raw_bytes
  2. DecodeCBE(raw_bytes) -> (value, consumed_bytes)
  3. ComputeHash(raw_bytes) -> sha1_hex
  4. DeriveUUID(namespace, payload) -> (sha1_hex, uuidv5_string)
*/
package adapter

import (
	"cortex-go/cbe"
)

// EncodeCBE serializes a CortexValue AST node into canonical CBE wire bytes.
func EncodeCBE(val cbe.CortexValue) ([]byte, error) {
	return cbe.Encode(val)
}

// DecodeCBE parses CBE wire bytes into a CortexValue AST node.
func DecodeCBE(rawBytes []byte) (cbe.CortexValue, int, error) {
	return cbe.Decode(rawBytes)
}

// ComputeHash computes the standalone SHA-1 hex digest of raw bytes.
func ComputeHash(rawBytes []byte) string {
	return cbe.ComputeSHA1(rawBytes)
}

// DeriveUUID computes the SHA-1 digest and RFC 4122 UUIDv5 string from an
// explicit 16-byte namespace and raw CBE payload bytes.
func DeriveUUID(namespace [16]byte, payload []byte) (string, string) {
	return cbe.ComputeRawUUIDv5(namespace, payload)
}
