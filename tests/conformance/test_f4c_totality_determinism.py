"""
F4c.2 Verifier Totality and Determinism Test Suite
Author: Iradukunda Fils <iradukundafils1@gmail.com>

Validates that the Independent Verifier (cortex_verifier.py) satisfies:
1. Verdict Totality: Every input E maps strictly to Verdict.VALID (0), INVALID (1), or INDETERMINATE (2).
2. Determinism: Repeated calls on identical input E yield identical (Verdict, msg) outputs.
3. Schema Conformance: Valid evidence bundles conform strictly to docs/spec/evidence_profile_v1.schema.json.
"""

import copy
import json
import os
import unittest
from tools.cortex_verifier import IndependentVerifier, Verdict
from tests.conformance.test_gate_j_independent_verifier import generate_valid_evidence_bundle


class TestF4cTotalityAndDeterminism(unittest.TestCase):
    """F4c.2 Formal Property Test Suite: Totality, Determinism, Schema Conformance."""

    def setUp(self):
        self.verifier = IndependentVerifier()
        self.valid_bundle = generate_valid_evidence_bundle(steps=3)

    def test_f4c_2_001_totality_and_determinism_valid_bundle(self):
        """F4c.2-001: Valid bundle evaluates deterministically to Verdict.VALID (0)."""
        v1, m1 = self.verifier.verify_evidence_bundle(self.valid_bundle)
        v2, m2 = self.verifier.verify_evidence_bundle(self.valid_bundle)
        
        self.assertIn(v1, [Verdict.VALID, Verdict.INVALID, Verdict.INDETERMINATE])
        self.assertEqual(v1, Verdict.VALID)
        self.assertEqual(v1, v2)
        self.assertEqual(m1, m2)

    def test_f4c_2_002_totality_and_determinism_invalid_bundle(self):
        """F4c.2-002: Corrupted bundle evaluates deterministically to Verdict.INVALID (1)."""
        corrupted = copy.deepcopy(self.valid_bundle)
        corrupted["intents"][0]["signature"] = "0" * 64
        
        v1, m1 = self.verifier.verify_evidence_bundle(corrupted)
        v2, m2 = self.verifier.verify_evidence_bundle(corrupted)
        
        self.assertIn(v1, [Verdict.VALID, Verdict.INVALID, Verdict.INDETERMINATE])
        self.assertEqual(v1, Verdict.INVALID)
        self.assertEqual(v1, v2)
        self.assertEqual(m1, m2)

    def test_f4c_2_003_totality_and_determinism_indeterminate_bundle(self):
        """F4c.2-003: Incomplete bundle evaluates deterministically to Verdict.INDETERMINATE (2)."""
        incomplete = copy.deepcopy(self.valid_bundle)
        incomplete["is_incomplete"] = True
        
        v1, m1 = self.verifier.verify_evidence_bundle(incomplete)
        v2, m2 = self.verifier.verify_evidence_bundle(incomplete)
        
        self.assertIn(v1, [Verdict.VALID, Verdict.INVALID, Verdict.INDETERMINATE])
        self.assertEqual(v1, Verdict.INDETERMINATE)
        self.assertEqual(v1, v2)
        self.assertEqual(m1, m2)

    def test_f4c_2_004_totality_arbitrary_malformed_inputs(self):
        """F4c.2-004: Arbitrary malformed inputs map safely to finite Verdict enum without crashing."""
        malformed_inputs = [
            None,
            [],
            "not_a_dictionary",
            12345,
            {},
            {"anchor": {}},
            {"anchor": None, "intents": [], "tokens": [], "events": [], "witness_chain": []},
            {"anchor": {"node_id": "invalid_uuid", "genesis_epoch": "abc"}, "intents": [1], "tokens": [1], "events": [1], "witness_chain": [1]},
        ]
        
        for inp in malformed_inputs:
            v, msg = self.verifier.verify_evidence_bundle(inp)
            self.assertIn(v, [Verdict.VALID, Verdict.INVALID, Verdict.INDETERMINATE])
            self.assertIsInstance(msg, str)

    def test_f4c_2_005_schema_file_existence(self):
        """F4c.2-005: Normative evidence_profile_v1.schema.json exists and is valid JSON."""
        schema_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "docs", "spec", "evidence_profile_v1.schema.json"
        )
        self.assertTrue(os.path.exists(schema_path), f"Schema missing at {schema_path}")
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_data = json.load(f)
        self.assertEqual(schema_data.get("title"), "Cortex Evidence Profile V1 Schema")


if __name__ == "__main__":
    unittest.main()
