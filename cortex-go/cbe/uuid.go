/*
SHA-1 + RFC 4122 UUIDv5 derivation with explicit namespace parameter.

Computes both raw SHA-1 digest and RFC 4122 Version 5 / Variant RFC 4122
UUIDv5 from raw byte sequences. The namespace is explicitly passed as a
16-byte array to prevent hidden global state or conflation with raw SHA-1.
*/
package cbe

import (
	"crypto/sha1"
	"fmt"
)

// NamespaceCortexSystem is the Cortex system namespace UUID as raw 16 bytes.
// Matches: a1b2c3d4-0000-5000-8000-000000000001
var NamespaceCortexSystem = [16]byte{
	0xa1, 0xb2, 0xc3, 0xd4, 0x00, 0x00, 0x50, 0x00,
	0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01,
}

// ComputeRawUUIDv5 computes the raw SHA-1 digest and RFC 4122 UUIDv5 string
// from an explicit 16-byte namespace and raw payload bytes.
//
// The SHA-1 preimage is: namespace_bytes || payload_bytes
//
// RFC 4122 bit masking:
//
//	digest[6] = (digest[6] & 0x0F) | 0x50  // Version 5
//	digest[8] = (digest[8] & 0x3F) | 0x80  // Variant RFC 4122
//
// Returns (sha1HexDigest, uuidv5String).
func ComputeRawUUIDv5(namespace [16]byte, payload []byte) (string, string) {
	h := sha1.New()
	h.Write(namespace[:])
	h.Write(payload)
	digest := h.Sum(nil) // 20 bytes

	sha1Hex := fmt.Sprintf("%x", digest)

	// Take first 16 bytes and apply RFC 4122 masking
	var raw16 [16]byte
	copy(raw16[:], digest[:16])
	raw16[6] = (raw16[6] & 0x0F) | 0x50 // Version 5
	raw16[8] = (raw16[8] & 0x3F) | 0x80 // Variant RFC 4122

	// Format as standard UUID string: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
	uuidStr := fmt.Sprintf("%08x-%04x-%04x-%04x-%012x",
		raw16[0:4],
		raw16[4:6],
		raw16[6:8],
		raw16[8:10],
		raw16[10:16],
	)

	return sha1Hex, uuidStr
}

// ComputeSHA1 computes the raw SHA-1 digest of the given byte slice.
// This is the standalone hash operation, independent of UUIDv5 namespace prefixing.
func ComputeSHA1(data []byte) string {
	h := sha1.New()
	h.Write(data)
	return fmt.Sprintf("%x", h.Sum(nil))
}
