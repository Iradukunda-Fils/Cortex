/*
CortexValue AST type system for language-neutral semantic value representation.

Implements the Revision #5 canonical type model: Null, Bool, Int, Float,
String, Bytes, List, Map. Constructors enforce strict invariants (INT64 bounds,
float finiteness, NFC key deduplication).
*/
package cbe

import (
	"fmt"
	"math"
)

const (
	// INT64 bounds for signed 64-bit integer validation.
	Int64Min = -9223372036854775808
	Int64Max = 9223372036854775807
)

// CortexValue is the interface satisfied by all CBE AST node types.
type CortexValue interface {
	cbeNode() // marker method for compile-time type safety
}

// MapPair represents a single key-value entry in a canonical Map.
type MapPair struct {
	Key   string
	Value CortexValue
}

// Null represents the CBE Null type.
type Null struct{}

func (Null) cbeNode() {}

// Bool represents the CBE Bool type (B1 / B0).
type Bool struct{ Value bool }

func (Bool) cbeNode() {}

// Int represents a CBE signed 64-bit integer.
type Int struct{ Value int64 }

func (Int) cbeNode() {}

// Float represents a CBE IEEE 754 64-bit double-precision float.
// Must be finite (NaN and ±Inf are forbidden by the specification).
type Float struct{ Value float64 }

func (Float) cbeNode() {}

// String represents a CBE Unicode string (NFC-normalized).
type String struct{ Value string }

func (String) cbeNode() {}

// Bytes represents a CBE raw byte sequence.
type Bytes struct{ Value []byte }

func (Bytes) cbeNode() {}

// List represents a CBE ordered container of CortexValue elements.
type List struct{ Elements []CortexValue }

func (List) cbeNode() {}

// Map represents a CBE key-value container with canonically sorted string keys.
type Map struct{ Pairs []MapPair }

func (Map) cbeNode() {}

// NewInt constructs an Int with INT64 bounds validation.
func NewInt(v int64) (Int, error) {
	// Go int64 inherently satisfies [-2^63, 2^63 - 1], so this is
	// primarily a documentation boundary. Overflow is caught at parse time.
	return Int{Value: v}, nil
}

// NewFloat constructs a Float with finiteness validation and -0.0 normalization.
func NewFloat(v float64) (Float, error) {
	if math.IsNaN(v) || math.IsInf(v, 0) {
		return Float{}, errFloatNonFinite(fmt.Sprintf("non-finite float value: %v", v))
	}
	// Normalize -0.0 to +0.0
	if v == 0 {
		v = 0
	}
	return Float{Value: v}, nil
}
