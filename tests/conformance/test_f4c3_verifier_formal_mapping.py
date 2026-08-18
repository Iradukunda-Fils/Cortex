"""
F4c.3 Verifier Formal Model Correspondence Test Suite
Author: Iradukunda Fils <iradukundafils1@gmail.com>

Verifies that the Python IndependentVerifier (cortex_verifier.py) decision procedure
strictly corresponds to the Coq formal specification (verification/GateF_F4c_VerifierSpec.v):
1. VERDICT_VALID (Coq) <-> Verdict.VALID (0) (Python)
2. VERDICT_INVALID (Coq) <-> Verdict.INVALID (1) (Python)
3. VERDICT_MALFORMED (Coq) <-> Verdict.INDETERMINATE (2) (Python)
"""

import copy
import json
import unittest
from tools.cortex_verifier import IndependentVerifier, Verdict
from tests.conformance.test_gate_j_independent_verifier import generate_valid_evidence_bundle


class TestF4c3VerifierFormalMapping(unittest.TestCase):
    """F4c.3 Property Harness: Verifier Implementation ↔ Coq Formal Model Correspondence."""

    def setUp(self):
        self.verifier = IndependentVerifier()
        self.valid_bundle = generate_valid_evidence_bundle(steps=3)

    def test_f4c3_001_valid_verdict_correspondence(self):
        """F4c.3-001: Valid evidence bundle maps to VERDICT_VALID / Verdict.VALID (0)."""
        verdict, msg = self.verifier.verify_evidence_bundle(self.valid_bundle)
        self.assertEqual(verdict, Verdict.VALID)
        self.assertIn("EVIDENCE_VERIFIED_VALID", msg)

    def test_f4c3_002_invalid_verdict_correspondence_digest_mismatch(self):
        """F4c.3-002: Corrupted event payload maps to VERDICT_INVALID / Verdict.INVALID (1)."""
        bundle = copy.deepcopy(self.valid_bundle)
        bundle["events"][0]["event"] = "MUTATED_EVENT"
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_EVENT_DIGEST_MISMATCH", msg)

    def test_f4c3_003_invalid_verdict_correspondence_signature(self):
        """F4c.3-003: Forged authority signature maps to VERDICT_INVALID / Verdict.INVALID (1)."""
        bundle = copy.deepcopy(self.valid_bundle)
        bundle["intents"][0]["signature"] = "0" * 64
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_SIGNATURE_INVALID", msg)

    def test_f4c3_004_malformed_verdict_correspondence_truncated_log(self):
        """F4c.3-004: Truncated witness chain maps to VERDICT_MALFORMED / Verdict.INDETERMINATE (2)."""
        bundle = copy.deepcopy(self.valid_bundle)
        bundle["witness_chain"] = []
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INDETERMINATE)
        self.assertIn("TRAP_INCOMPLETE_TRACE", msg)

    def test_f4c3_005_malformed_verdict_correspondence_length_mismatch(self):
        """F4c.3-005: Stream length mismatch maps to VERDICT_MALFORMED / Verdict.INDETERMINATE (2)."""
        bundle = copy.deepcopy(self.valid_bundle)
        bundle["events"].pop()
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INDETERMINATE)
        self.assertIn("TRAP_INCOMPLETE_TRACE_STREAM_LENGTH_MISMATCH", msg)

    def test_f4c3_006_sequence_continuity_trap(self):
        """F4c.3-006: Non-monotonic sequence gap maps to VERDICT_INVALID / Verdict.INVALID (1)."""
        bundle = copy.deepcopy(self.valid_bundle)
        bundle["witness_chain"][1]["sequence"] = 99
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_SEQUENCE_GAP", msg)

    def test_f4c3_007_parent_pointer_chaining_trap(self):
        """F4c.3-007: Broken parent pointer chaining maps to VERDICT_INVALID / Verdict.INVALID (1)."""
        bundle = copy.deepcopy(self.valid_bundle)
        bundle["witness_chain"][1]["prev_witness"] = "f" * 64
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_CHAIN_BROKEN", msg)


if __name__ == "__main__":
    unittest.main()
