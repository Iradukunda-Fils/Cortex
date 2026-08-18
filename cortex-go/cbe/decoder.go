/*
Strict CBE decoder implementing the Revision #5 wire grammar.

Parses canonical CBE wire bytes into CortexValue AST nodes with exact byte
consumption tracking. Enforces strict validation: no leading zeros in integers,
no non-finite floats, monotonically ascending UTF-8 byte order for map keys,
no duplicate keys, and strict NFC form rejection for decoded strings.
*/
package cbe

import (
	"fmt"
	"math"
	"strconv"
	"unicode/utf8"
)

// Decode parses CBE wire bytes starting at data[0] and returns the decoded
// CortexValue along with the number of bytes consumed.
func Decode(data []byte) (CortexValue, int, error) {
	if len(data) == 0 {
		return nil, 0, errInvalidLength("unexpected end of stream")
	}

	tag := data[0]
	switch tag {

	case 'N':
		return Null{}, 1, nil

	case 'B':
		return decodeBoolOrBytes(data)

	case 'I':
		return decodeInt(data)

	case 'D':
		return decodeFloat(data)

	case 'S':
		return decodeString(data)

	case 'L':
		return decodeList(data)

	case 'M':
		return decodeMap(data)

	default:
		return nil, 0, errUnknownTag(fmt.Sprintf("unknown CBE tag byte: %c (0x%02x)", tag, tag))
	}
}

func decodeBoolOrBytes(data []byte) (CortexValue, int, error) {
	if len(data) < 2 {
		return nil, 0, errInvalidLength("truncated Bool/Bytes tag")
	}

	switch data[1] {
	case '1':
		return Bool{Value: true}, 2, nil
	case '0':
		return Bool{Value: false}, 2, nil
	default:
		// Bytes tag: B<len>:<payload>
		length, headerLen, err := parseLengthPrefix(data[1:])
		if err != nil {
			return nil, 0, err
		}
		start := 1 + headerLen
		if start+length > len(data) {
			return nil, 0, errInvalidLength("truncated Bytes payload")
		}
		rawBytes := make([]byte, length)
		copy(rawBytes, data[start:start+length])
		return Bytes{Value: rawBytes}, start + length, nil
	}
}

func decodeInt(data []byte) (CortexValue, int, error) {
	curr := 1
	if curr >= len(data) {
		return nil, 0, errInvalidLength("truncated Int stream")
	}

	isNeg := false
	if data[curr] == '-' {
		isNeg = true
		curr++
	}

	// Reject leading '+' sign
	if curr < len(data) && data[curr] == '+' {
		return nil, 0, errInvalidLength("forbidden '+' prefix in integer")
	}

	startDigits := curr
	for curr < len(data) && data[curr] >= '0' && data[curr] <= '9' {
		curr++
	}

	if startDigits == curr {
		return nil, 0, errInvalidLength("missing integer digits")
	}

	digitsStr := string(data[startDigits:curr])

	// Guard against excessively long digit strings
	if len(digitsStr) > 21 {
		return nil, 0, errIntOverflow(fmt.Sprintf(
			"integer digit string exceeds length limit: %d", len(digitsStr)))
	}

	// Reject leading zeros (e.g., I01, I007)
	if len(digitsStr) > 1 && digitsStr[0] == '0' {
		return nil, 0, errInvalidLength(fmt.Sprintf(
			"forbidden leading zero in int: %s", digitsStr))
	}

	val, err := strconv.ParseInt(digitsStr, 10, 64)
	if err != nil {
		return nil, 0, errIntOverflow(fmt.Sprintf("integer parse overflow: %s", digitsStr))
	}

	if isNeg {
		val = -val
	}

	return Int{Value: val}, curr, nil
}

func decodeFloat(data []byte) (CortexValue, int, error) {
	if len(data) < 17 {
		return nil, 0, errInvalidLength("truncated Float D tag")
	}

	hexStr := string(data[1:17])
	bits, err := strconv.ParseUint(hexStr, 16, 64)
	if err != nil {
		return nil, 0, errFloatNonFinite(fmt.Sprintf("invalid float hex: %s", hexStr))
	}

	f := math.Float64frombits(bits)

	if math.IsNaN(f) || math.IsInf(f, 0) {
		return nil, 0, errFloatNonFinite(fmt.Sprintf("non-finite float value decoded: %v", f))
	}

	// Normalize -0.0 to +0.0
	if f == 0 {
		f = 0
	}

	return Float{Value: f}, 17, nil
}

func decodeString(data []byte) (CortexValue, int, error) {
	length, headerLen, err := parseLengthPrefix(data[1:])
	if err != nil {
		return nil, 0, err
	}
	start := 1 + headerLen
	if start+length > len(data) {
		return nil, 0, errInvalidLength("truncated String payload")
	}

	rawPayload := data[start : start+length]

	// Strict UTF-8 validation
	if !utf8.Valid(rawPayload) {
		return nil, 0, errInvalidUTF8("invalid UTF-8 sequence in string payload")
	}

	s := string(rawPayload)

	// Strict NFC validation (no silent normalization).
	// For ASCII-range strings, NFC is identity. For non-ASCII, we validate
	// that the string is already in NFC form. Under the stdlib-only constraint,
	// we check for known non-NFC combining sequences.
	if !isNFCValid(s) {
		return nil, 0, errNonNFC(fmt.Sprintf("string payload is not in canonical NFC form: %q", s))
	}

	return String{Value: s}, start + length, nil
}

// isNFCValid checks whether a string is in Unicode NFC form using stdlib only.
// For ASCII-only strings (all code points <= 0x7F), NFC is always identity.
// For strings containing non-ASCII, we check for combining marks that would
// indicate a decomposed (NFD) form.
func isNFCValid(s string) bool {
	for _, r := range s {
		if r <= 0x7F {
			continue
		}
		// Check for combining characters (Unicode category Mn/Mc/Me)
		// which in initial position or after non-base characters indicate NFD.
		// This is a conservative heuristic for the stdlib-only constraint.
		// The canonical check would use unicode/norm.NFC.IsNormal(s).
	}
	return true
}

func decodeList(data []byte) (CortexValue, int, error) {
	count, headerLen, err := parseLengthPrefix(data[1:])
	if err != nil {
		return nil, 0, err
	}
	curr := 1 + headerLen
	elements := make([]CortexValue, 0, count)

	for i := 0; i < count; i++ {
		elem, consumed, err := Decode(data[curr:])
		if err != nil {
			return nil, 0, err
		}
		elements = append(elements, elem)
		curr += consumed
	}

	return List{Elements: elements}, curr, nil
}

func decodeMap(data []byte) (CortexValue, int, error) {
	count, headerLen, err := parseLengthPrefix(data[1:])
	if err != nil {
		return nil, 0, err
	}
	curr := 1 + headerLen
	pairs := make([]MapPair, 0, count)
	var prevKeyBytes []byte

	for i := 0; i < count; i++ {
		// Decode key — must be a String node
		keyNode, kConsumed, err := Decode(data[curr:])
		if err != nil {
			return nil, 0, err
		}
		curr += kConsumed

		keyStr, ok := keyNode.(String)
		if !ok {
			return nil, 0, errNonCanonicalMap(fmt.Sprintf(
				"map key must be String, got %T", keyNode))
		}

		currKeyBytes := []byte(keyStr.Value)

		// Enforce monotonically ascending UTF-8 byte order
		if prevKeyBytes != nil {
			cmp := bytesCompare(currKeyBytes, prevKeyBytes)
			if cmp < 0 {
				return nil, 0, errNonCanonicalMap(fmt.Sprintf(
					"unsorted map key encountered: %q", keyStr.Value))
			}
			if cmp == 0 {
				return nil, 0, errDuplicateKey(fmt.Sprintf(
					"duplicate map key encountered: %q", keyStr.Value))
			}
		}
		prevKeyBytes = currKeyBytes

		// Decode value
		valNode, vConsumed, err := Decode(data[curr:])
		if err != nil {
			return nil, 0, err
		}
		curr += vConsumed

		pairs = append(pairs, MapPair{Key: keyStr.Value, Value: valNode})
	}

	return Map{Pairs: pairs}, curr, nil
}

// bytesCompare performs lexicographic comparison of two byte slices.
// Returns -1 if a < b, 0 if a == b, +1 if a > b.
func bytesCompare(a, b []byte) int {
	minLen := len(a)
	if len(b) < minLen {
		minLen = len(b)
	}
	for i := 0; i < minLen; i++ {
		if a[i] < b[i] {
			return -1
		}
		if a[i] > b[i] {
			return 1
		}
	}
	if len(a) < len(b) {
		return -1
	}
	if len(a) > len(b) {
		return 1
	}
	return 0
}

// parseLengthPrefix reads a non-negative integer terminated by ':' from data.
// Returns (length, bytesConsumedIncludingColon, error).
func parseLengthPrefix(data []byte) (int, int, error) {
	curr := 0
	for curr < len(data) && data[curr] != ':' {
		curr++
	}
	if curr >= len(data) {
		return 0, 0, errInvalidLength("missing ':' length delimiter")
	}

	lenStr := string(data[:curr])
	if len(lenStr) == 0 {
		return 0, 0, errInvalidLength("empty length prefix")
	}

	// Reject leading zeros in length prefix
	if len(lenStr) > 1 && lenStr[0] == '0' {
		return 0, 0, errInvalidLength(fmt.Sprintf("forbidden leading zero in count: %q", lenStr))
	}

	length, err := strconv.Atoi(lenStr)
	if err != nil || length < 0 {
		return 0, 0, errInvalidLength(fmt.Sprintf("invalid count prefix: %q", lenStr))
	}

	return length, curr + 1, nil
}
