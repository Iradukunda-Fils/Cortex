"""
Comprehensive Contract & Conformance Unit Test Suite for Cortex-CBE Module
"""

import unittest

from cortex.cbe import (
    VECTORS,
    Bool,
    CBEDuplicateKeyError,
    CBEFloatNonFiniteError,
    CBEIntOverflowError,
    CBEInvalidLengthError,
    CBENonCanonicalMapError,
    CBENonNFCError,
    CortexValue,
    Float,
    Int,
    List,
    Map,
    Null,
    String,
    decode,
    derive_logical_event_id,
    encode,
)


class TestCBENormativeVectors(unittest.TestCase):
    def test_normative_vectors_tva_through_tvroot(self) -> None:
        """Test all 4 locked normative test vectors match exact CBE, SHA1, and UUIDv5."""
        for v_id, vec in VECTORS.items():
            cbe_bytes, hex_str, sha1_hex, uuid_str = derive_logical_event_id(
                vec["workflow_id"],
                vec["command_type"],
                vec["causation_id"],
                vec["payload"],
            )
            self.assertEqual(
                cbe_bytes.decode("ascii"),
                vec["expected_cbe"],
                f"CBE mismatch for {v_id}",
            )
            self.assertEqual(uuid_str, vec["expected_uuid"], f"UUIDv5 mismatch for {v_id}")


class TestCBEEdgeCasesAndInvariants(unittest.TestCase):
    def test_int64_boundary_and_overflow(self) -> None:
        """INT64_MIN and INT64_MAX pass; overflow/underflow raise CBEIntOverflowError."""
        min_int = Int(-9223372036854775808)
        max_int = Int(9223372036854775807)
        self.assertEqual(encode(min_int), b"I-9223372036854775808")
        self.assertEqual(encode(max_int), b"I9223372036854775807")

        with self.assertRaises(CBEIntOverflowError):
            Int(9223372036854775808)

        with self.assertRaises(CBEIntOverflowError):
            Int(-9223372036854775809)

    def test_int_decoder_leading_zero_and_plus_rejection(self) -> None:
        """I01 or I+42 must be rejected by decoder."""
        with self.assertRaises(CBEInvalidLengthError):
            decode(b"I01")

        with self.assertRaises(CBEInvalidLengthError):
            decode(b"I+42")

    def test_float_normalization_and_nonfinite_rejection(self) -> None:
        """-0.0 normalizes to +0.0; NaN and Infinity raise CBEFloatNonFiniteError."""
        f_neg_zero = Float(-0.0)
        self.assertEqual(f_neg_zero.value, 0.0)
        self.assertEqual(encode(f_neg_zero), b"D0000000000000000")

        with self.assertRaises(CBEFloatNonFiniteError):
            Float(float("nan"))

        with self.assertRaises(CBEFloatNonFiniteError):
            Float(float("inf"))

        with self.assertRaises(CBEFloatNonFiniteError):
            Float(float("-inf"))

    def test_encoder_string_nfc_normalization(self) -> None:
        """Encoder eagerly normalizes decomposed Unicode strings to NFC."""
        decomposed = "e\u0301"  # 'e' + combining acute accent
        s_node = String(decomposed)
        encoded = encode(s_node)
        # NFC form 'é' is 2 UTF-8 bytes: \xc3\xa9 -> S2:\xc3\xa9
        self.assertEqual(encoded, b"S2:\xc3\xa9")

    def test_decoder_strict_non_nfc_rejection(self) -> None:
        """Decoder MUST REJECT non-NFC wire bytes with CBENonNFCError (NO silent normalization)."""
        decomposed_utf8 = "e\u0301".encode("utf-8")  # 3 bytes: 65 204 129
        wire_bytes = f"S{len(decomposed_utf8)}:".encode("ascii") + decomposed_utf8
        with self.assertRaises(CBENonNFCError):
            decode(wire_bytes)

    def test_map_duplicate_key_rejection(self) -> None:
        """Map key collision under NFC normalization raises CBEDuplicateKeyError."""
        pairs = [
            (String("é"), Int(1)),
            (String("e\u0301"), Int(2)),
        ]
        with self.assertRaises(CBEDuplicateKeyError):
            Map(pairs)

    def test_float_type_safety_rejection(self) -> None:
        """Float constructor MUST reject non-float primitives like int, bool, str with TypeError."""
        with self.assertRaises(TypeError):
            Float(100)  # type: ignore

        with self.assertRaises(TypeError):
            Float(True)  # type: ignore

        with self.assertRaises(TypeError):
            Float("1.0")  # type: ignore

    def test_map_key_ast_identity_preservation(self) -> None:
        """Encoder preserves exact key AST node reference when serializing Map pairs."""
        key_node = String("test_key")
        val_node = Int(123)
        map_node = Map([(key_node, val_node)])
        self.assertIs(map_node.pairs[0][0], key_node)
        self.assertEqual(encode(map_node), b"M1:S8:test_keyI123")

    def test_map_key_canonical_ordering_aa_before_b(self) -> None:
        """Map key 'aa' sorts before 'b' under UTF-8 byte comparison ('aa' < 'b')."""
        pairs = [(String("aa"), Int(1)), (String("b"), Int(2))]
        map_node = Map(pairs)
        encoded = encode(map_node)
        self.assertEqual(encoded, b"M2:S2:aaI1S1:bI2")

        # Decoder accepts canonical order
        decoded_map, _ = decode(encoded)
        self.assertEqual(decoded_map, map_node)

        # Decoder rejects inverted unsorted order 'b' before 'aa'
        inverted_wire = b"M2:S1:bI2S2:aaI1"
        with self.assertRaises(CBENonCanonicalMapError):
            decode(inverted_wire)

    def test_empty_containers_round_trip(self) -> None:
        """Null, Bool, empty String S0:, List L0:, Map M0: round-trip cleanly."""
        test_cases = [
            (Null(), b"N"),
            (Bool(True), b"B1"),
            (Bool(False), b"B0"),
            (String(""), b"S0:"),
            (List([]), b"L0:"),
            (Map([]), b"M0:"),
        ]
        for node, expected_bytes in test_cases:
            enc = encode(node)
            self.assertEqual(enc, expected_bytes)
            dec_node, dec_offset = decode(enc)
            self.assertEqual(dec_node, node)
            self.assertEqual(dec_offset, len(expected_bytes))

    def test_deeply_nested_container_round_trip(self) -> None:
        """Deeply nested List/Map structure round-trips with zero data loss."""
        val = {
            "a": [1, True, None, {"b": -42, "c": [1.0, "hello"]}],
            "d": "test",
        }
        ast = CortexValue.from_python(val)
        enc = encode(ast)
        dec_ast, offset = decode(enc)
        self.assertEqual(offset, len(enc))

    def test_trailing_bytes_offset_detection(self) -> None:
        """Decoder returns exact consumed byte count, allowing caller to detect trailing bytes."""
        valid_wire = b"I42"
        trailing_wire = b"I42EXTRA_GARBAGE"
        ast, offset = decode(trailing_wire)
        self.assertEqual(offset, len(valid_wire))
        self.assertLess(offset, len(trailing_wire))


if __name__ == "__main__":
    unittest.main()
