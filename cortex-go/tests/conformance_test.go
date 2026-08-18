/*
Phase 3.1 Go CBE Gate E Conformance Test Suite (Hardened)

MANDATORY GOVERNANCE COMPLIANCE:
 1. MANIFEST PROVENANCE & READ-ONLY HARD LOCK:
    - Validates SHA-256 of all 12 frozen artifact files against pre-existing constants.
    - Aborts immediately if any artifact has been altered or regenerated.
 2. ZERO EXTERNAL DEPENDENCY:
    - Pure Go stdlib execution (crypto/sha1, crypto/sha256). No Python, Rust, or FFI.
 3. DUAL-DIRECTION ROUND-TRIP VERIFICATION:
    - decode(frozenCBE) → AST → encode(AST) == frozenCBE (byte-exact)
 4. CRYPTOGRAPHIC INPUT PROVENANCE:
    - Computes and prints exact SHA-1 preimage trace (Namespace_Bytes || CBE_Bytes).
    - Independently derives UUIDv5 and asserts against frozen .uuid artifact.
*/
package tests

import (
	"crypto/sha256"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"cortex-go/cbe"
)

// Pre-existing frozen SHA-256 manifest constants (immutable oracle).
var frozenManifestSHA256 = map[string]string{
	"tv-a.cbe":     "64b199ea01a788553cc95b193629d25d46b03f76f960b1d4f50ac420f82f4125",
	"tv-a.sha1":    "9602e438601eaf9f570ae7fc98854a9adaca30ffb1c74e3705cf6a3301c4c341",
	"tv-a.uuid":    "3d6ec74d4f9c482d54a9b8710a0a8751c8c46fa24c59467a8611778b10ed6f8e",
	"tv-b.cbe":     "6bb283fc20ae27e2f793c21e8d2d2264a6fb0fda7ba73e4544d1ded09bd8e512",
	"tv-b.sha1":    "48f6c6c9111de3084b8812263ddf4f1f2c81cc9ce5bef2b4fce363897d0981c0",
	"tv-b.uuid":    "625634e04dfd4727a51c778dc7c78cc5159500112accb221590ac37c9d5940eb",
	"tv-c.cbe":     "96cac57eb5941a8ec367ffe5e98bbff061858cc8387fa404cb5d9ad428151cbf",
	"tv-c.sha1":    "a70e80615ad52d01b1e95f198b667b5dfd62827e9555c4359d8a5cce335d3a88",
	"tv-c.uuid":    "15034006695120f7cec81617c463653a1353e347f92e9111df16fadabee84336",
	"tv-root.cbe":  "86fad8e2978d61dcef218a1eb6fce53a39913f040a60eec71eafaad231e1d589",
	"tv-root.sha1": "c786cbdb18eea02e56546dd8282ccec91471fe7c3ab21af16efa32eca0976002",
	"tv-root.uuid": "4a6455bfe447f0e36386f7e19d854e4d8b4b1bd8393ac72b17e09318d3036a62",
}

func getArtifactDir() string {
	_, filename, _, _ := runtime.Caller(0)
	return filepath.Join(filepath.Dir(filename), "..", "..", "research", "formalization", "artifacts")
}

func toHexString(data []byte) string {
	result := make([]byte, 0, len(data)*2)
	for _, b := range data {
		result = append(result, fmt.Sprintf("%02x", b)...)
	}
	return string(result)
}

func verifyManifestIntegrity(t *testing.T) {
	t.Helper()
	dir := getArtifactDir()
	for filename, expectedSHA256 := range frozenManifestSHA256 {
		filePath := filepath.Join(dir, filename)
		content, err := os.ReadFile(filePath)
		if err != nil {
			t.Fatalf("MANIFEST INTEGRITY ERROR: Missing artifact file %s: %v", filePath, err)
		}
		hash := sha256.Sum256(content)
		actualSHA256 := toHexString(hash[:])
		if actualSHA256 != expectedSHA256 {
			t.Fatalf("MANIFEST INTEGRITY FAILURE: Frozen artifact %s has been modified! Expected %s, got %s",
				filename, expectedSHA256, actualSHA256)
		}
	}
	t.Log("[✓] MANIFEST ANTI-CIRCULARITY CHECK PASSED: All 12 artifact files match frozen SHA-256 oracle.")
}

func testVectorConformance(t *testing.T, name string) {
	t.Helper()
	verifyManifestIntegrity(t)

	dir := getArtifactDir()

	// Read frozen artifacts
	frozenCBEBytes, err := os.ReadFile(filepath.Join(dir, name+".cbe"))
	if err != nil {
		t.Fatalf("Failed to read CBE artifact %s: %v", name, err)
	}

	frozenSHA1Content, err := os.ReadFile(filepath.Join(dir, name+".sha1"))
	if err != nil {
		t.Fatalf("Failed to read SHA1 artifact %s: %v", name, err)
	}
	expectedSHA1Hex := strings.TrimSpace(string(frozenSHA1Content))

	frozenUUIDContent, err := os.ReadFile(filepath.Join(dir, name+".uuid"))
	if err != nil {
		t.Fatalf("Failed to read UUID artifact %s: %v", name, err)
	}
	expectedUUIDStr := strings.TrimSpace(string(frozenUUIDContent))

	// 1. Calculate CBE SHA-256 for audit trail
	cbeSHA256 := sha256.Sum256(frozenCBEBytes)
	cbeSHA256Hex := toHexString(cbeSHA256[:])

	// 2. Decode frozen wire bytes to AST
	astNode, consumed, err := cbe.Decode(frozenCBEBytes)
	if err != nil {
		t.Fatalf("%s: Failed to decode frozen CBE wire bytes: %v", name, err)
	}
	if consumed != len(frozenCBEBytes) {
		t.Fatalf("%s: decoder consumed %d bytes, expected %d", name, consumed, len(frozenCBEBytes))
	}

	// 3. Re-encode AST and verify exact byte match (ROUND-TRIP)
	reEncodedBytes, err := cbe.Encode(astNode)
	if err != nil {
		t.Fatalf("%s: Failed to re-encode AST: %v", name, err)
	}
	if string(reEncodedBytes) != string(frozenCBEBytes) {
		t.Fatalf("%s: CBE round-trip MISMATCH!\n  frozen: %s\n  re-enc: %s",
			name, toHexString(frozenCBEBytes), toHexString(reEncodedBytes))
	}

	// 4. Cryptographic Input Provenance Trace
	namespaceHex := toHexString(cbe.NamespaceCortexSystem[:])
	cbeHex := toHexString(frozenCBEBytes)

	// Build preimage: namespace_bytes || cbe_bytes
	var preimage []byte
	preimage = append(preimage, cbe.NamespaceCortexSystem[:]...)
	preimage = append(preimage, frozenCBEBytes...)
	preimageHex := toHexString(preimage)

	// Compute SHA-1 and UUIDv5 independently
	computedSHA1Hex, computedUUIDStr := cbe.ComputeRawUUIDv5(cbe.NamespaceCortexSystem, frozenCBEBytes)

	// Assert SHA-1 matches frozen artifact
	if computedSHA1Hex != expectedSHA1Hex {
		t.Fatalf("%s: SHA-1 MISMATCH!\n  expected: %s\n  computed: %s",
			name, expectedSHA1Hex, computedSHA1Hex)
	}

	// Assert UUIDv5 matches frozen artifact
	if computedUUIDStr != expectedUUIDStr {
		t.Fatalf("%s: UUIDv5 MISMATCH!\n  expected: %s\n  computed: %s",
			name, expectedUUIDStr, computedUUIDStr)
	}

	// Print full audit provenance trace
	t.Logf("============================================================")
	t.Logf("CRYPTOGRAPHIC INPUT PROVENANCE PROOF: %s", name)
	t.Logf("  cbe_sha256:                      %s", cbeSHA256Hex)
	t.Logf("  cbe_length:                      %d bytes", len(frozenCBEBytes))
	t.Logf("  namespace_hex:                   %s", namespaceHex)
	t.Logf("  cbe_hex:                         %s", cbeHex)
	t.Logf("  concatenated_sha1_preimage_hex:  %s", preimageHex)
	t.Logf("  sha1_digest_hex:                 %s", computedSHA1Hex)
	t.Logf("  frozen_uuid:                     %s", expectedUUIDStr)
	t.Logf("  go_derived_uuid:                 %s", computedUUIDStr)
	t.Logf("  round_trip:                      PASS")
	t.Logf("  exact_match:                     PASS")
	t.Logf("============================================================")
}

// =============================================================================
// NORMATIVE VECTOR TESTS (TV-A through TV-Root)
// =============================================================================

func TestVectorTVA(t *testing.T) {
	testVectorConformance(t, "tv-a")
}

func TestVectorTVB(t *testing.T) {
	testVectorConformance(t, "tv-b")
}

func TestVectorTVC(t *testing.T) {
	testVectorConformance(t, "tv-c")
}

func TestVectorTVRoot(t *testing.T) {
	testVectorConformance(t, "tv-root")
}

// =============================================================================
// ADVERSARIAL REJECTION TESTS
// =============================================================================

func TestAdversarialNonCanonicalMapRejection(t *testing.T) {
	// Map with keys "b" before "aa" — must reject as unsorted
	malformedWire := []byte("M2:S1:bI1S2:aaI2")
	_, _, err := cbe.Decode(malformedWire)
	if err == nil {
		t.Fatal("Expected NonCanonicalMap error, got nil")
	}
	if cbe.ErrorCode(err) != cbe.CodeNonCanonicalMap {
		t.Fatalf("Expected error code %s, got %s: %v",
			cbe.CodeNonCanonicalMap, cbe.ErrorCode(err), err)
	}
}

func TestAdversarialDuplicateKeyRejection(t *testing.T) {
	// Encode a Map with duplicate keys
	duplicateMap := cbe.Map{Pairs: []cbe.MapPair{
		{Key: "key", Value: cbe.Int{Value: 1}},
		{Key: "key", Value: cbe.Int{Value: 2}},
	}}
	_, err := cbe.Encode(duplicateMap)
	if err == nil {
		t.Fatal("Expected DuplicateKey error, got nil")
	}
	if cbe.ErrorCode(err) != cbe.CodeDuplicateKey {
		t.Fatalf("Expected error code %s, got %s: %v",
			cbe.CodeDuplicateKey, cbe.ErrorCode(err), err)
	}
}

func TestAdversarialNonFiniteFloatRejection(t *testing.T) {
	// NaN
	_, err := cbe.Encode(cbe.Float{Value: math.NaN()})
	if err == nil {
		t.Fatal("Expected FloatNonFinite error for NaN, got nil")
	}
	if cbe.ErrorCode(err) != cbe.CodeFloatNonFinite {
		t.Fatalf("Expected error code %s, got %s: %v",
			cbe.CodeFloatNonFinite, cbe.ErrorCode(err), err)
	}

	// +Inf
	_, err = cbe.Encode(cbe.Float{Value: math.Inf(1)})
	if err == nil {
		t.Fatal("Expected FloatNonFinite error for +Inf, got nil")
	}

	// -Inf
	_, err = cbe.Encode(cbe.Float{Value: math.Inf(-1)})
	if err == nil {
		t.Fatal("Expected FloatNonFinite error for -Inf, got nil")
	}
}

func TestAdversarialIntegerOverflowRejection(t *testing.T) {
	// Digit string exceeding 21 chars
	malformedWire := []byte("I12345678901234567890123")
	_, _, err := cbe.Decode(malformedWire)
	if err == nil {
		t.Fatal("Expected IntOverflow error, got nil")
	}
	if cbe.ErrorCode(err) != cbe.CodeIntOverflow {
		t.Fatalf("Expected error code %s, got %s: %v",
			cbe.CodeIntOverflow, cbe.ErrorCode(err), err)
	}
}

func TestAdversarialLeadingZeroRejection(t *testing.T) {
	// I01 — leading zero forbidden
	malformedWire := []byte("I01")
	_, _, err := cbe.Decode(malformedWire)
	if err == nil {
		t.Fatal("Expected error for leading zero integer I01, got nil")
	}
}

func TestAdversarialTruncatedFrame(t *testing.T) {
	// Truncated String payload
	truncated := []byte("S10:abc")
	_, _, err := cbe.Decode(truncated)
	if err == nil {
		t.Fatal("Expected InvalidLength error for truncated frame, got nil")
	}
	if cbe.ErrorCode(err) != cbe.CodeInvalidLength {
		t.Fatalf("Expected error code %s, got %s: %v",
			cbe.CodeInvalidLength, cbe.ErrorCode(err), err)
	}
}

func TestAdversarialUnknownTag(t *testing.T) {
	// Unknown tag byte 'Z'
	malformed := []byte("Z123")
	_, _, err := cbe.Decode(malformed)
	if err == nil {
		t.Fatal("Expected UnknownTag error, got nil")
	}
	if cbe.ErrorCode(err) != cbe.CodeUnknownTag {
		t.Fatalf("Expected error code %s, got %s: %v",
			cbe.CodeUnknownTag, cbe.ErrorCode(err), err)
	}
}

func TestCanonicalMapKeyOrdering(t *testing.T) {
	// Encode a map where "aa" must sort before "b" under UTF-8 byte order
	m := cbe.Map{Pairs: []cbe.MapPair{
		{Key: "b", Value: cbe.Int{Value: 2}},
		{Key: "aa", Value: cbe.Int{Value: 1}},
	}}
	encoded, err := cbe.Encode(m)
	if err != nil {
		t.Fatalf("Failed to encode map: %v", err)
	}

	// Expected: M2:S2:aaI1S1:bI2 ("aa" before "b")
	expected := "M2:S2:aaI1S1:bI2"
	if string(encoded) != expected {
		t.Fatalf("Canonical map key ordering failed!\n  expected: %s\n  got:      %s",
			expected, string(encoded))
	}
}
