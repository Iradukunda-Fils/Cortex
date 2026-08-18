"""
F4c.4 Domain Closure Audit & Equivalence Test Suite
Author: Iradukunda Fils <iradukundafils1@gmail.com>

Differential testing of Python IndependentVerifier (cortex_verifier.py) against
the 10 partitioned equivalence classes of Evidence Profile V1 domain D_V1.

Asserts:
1. Class 1 (Valid Trace) -> Verdict.VALID (0)
2. Classes 2-7 (Invalid Invariants) -> Verdict.INVALID (1)
3. Classes 8-10 (Indeterminate / Incomplete) -> Verdict.INDETERMINATE (2)
"""

import copy
import unittest

from tests.conformance.test_gate_j_independent_verifier import generate_valid_evidence_bundle
from tools.cortex_verifier import IndependentVerifier, Verdict


class TestF4c4DomainClosureAudit(unittest.TestCase):
    """F4c.4 Property & Differential Test Suite across 10 Equivalence Classes of D_V1."""

    def setUp(self):
        self.verifier = IndependentVerifier()
        self.valid_bundle = generate_valid_evidence_bundle(steps=4)

    def test_class_1_full_verified_valid_trace(self):
        """Class 1: Complete and valid evidence bundle yields Verdict.VALID (0)."""
        verdict, msg = self.verifier.verify_evidence_bundle(self.valid_bundle)
        self.assertEqual(verdict, Verdict.VALID)
        self.assertIn("EVIDENCE_VERIFIED_VALID", msg)

    def test_class_2_anchor_mismatch(self):
        """Class 2: Genesis anchor mismatch yields Verdict.INVALID (1)."""
        bundle = copy.deepcopy(self.valid_bundle)
        bundle["anchor"]["expected_w0"] = "0" * 64
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_UNTRUSTED_ANCHOR_MISMATCH", msg)

    def test_class_3_signature_violation(self):
        """Class 3: Forged authority signature yields Verdict.INVALID (1)."""
        bundle = copy.deepcopy(self.valid_bundle)
        bundle["witness_chain"][0]["signature"] = "a" * 64
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_WITNESS_ENTRY_SIGNATURE_INVALID", msg)

    def test_class_4_token_parity_mismatch(self):
        """Class 4: Unbound token intent hash mismatch yields Verdict.INVALID (1)."""
        bundle = copy.deepcopy(self.valid_bundle)
        bundle["tokens"][0]["intent_hash"] = "f" * 64
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_TOKEN_PARITY_MISMATCH", msg)

    def test_class_5_sequence_gap(self):
        """Class 5: Discontinuous sequence gap yields Verdict.INVALID (1)."""
        bundle = copy.deepcopy(self.valid_bundle)
        bundle["witness_chain"][2]["sequence"] = 100
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_SEQUENCE_GAP", msg)

    def test_class_6_chain_broken(self):
        """Class 6: Discontinuous parent pointer yields Verdict.INVALID (1)."""
        bundle = copy.deepcopy(self.valid_bundle)
        bundle["witness_chain"][1]["prev_witness"] = "1" * 64
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_CHAIN_BROKEN", msg)

    def test_class_7_digest_mutation(self):
        """Class 7: Modified commit event payload yields Verdict.INVALID (1)."""
        bundle = copy.deepcopy(self.valid_bundle)
        bundle["events"][1]["tampered"] = True
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_EVENT_DIGEST_MISMATCH", msg)

    def test_class_8_empty_stream(self):
        """Class 8: Empty witness chain stream yields Verdict.INDETERMINATE (2)."""
        bundle = copy.deepcopy(self.valid_bundle)
        bundle["witness_chain"] = []
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INDETERMINATE)
        self.assertIn("TRAP_INCOMPLETE_TRACE", msg)

    def test_class_9_missing_required_section(self):
        """Class 9: Missing anchor section yields Verdict.INDETERMINATE (2)."""
        bundle = copy.deepcopy(self.valid_bundle)
        del bundle["anchor"]
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INDETERMINATE)
        self.assertIn("TRAP_INCOMPLETE_TRACE_MISSING_ANCHOR", msg)

    def test_class_10_stream_length_mismatch_and_flagged(self):
        """Class 10: Stream length mismatch or explicit incomplete flag yields Verdict.INDETERMINATE (2)."""
        bundle = copy.deepcopy(self.valid_bundle)
        bundle["events"].pop()
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INDETERMINATE)
        self.assertIn("TRAP_INCOMPLETE_TRACE_STREAM_LENGTH_MISMATCH", msg)

        # Explicitly flagged incomplete trace
        bundle2 = copy.deepcopy(self.valid_bundle)
        bundle2["is_incomplete"] = True
        verdict2, msg2 = self.verifier.verify_evidence_bundle(bundle2)
        self.assertEqual(verdict2, Verdict.INDETERMINATE)
        self.assertIn("TRAP_INCOMPLETE_TRACE_FLAGGED", msg2)


if __name__ == "__main__":
    unittest.main()
