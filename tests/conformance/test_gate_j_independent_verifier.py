"""
Gate J: Independent Standalone Verifier (P4) Test Suite
Author: Iradukunda Fils <iradukundafils1@gmail.com>
"""

import hashlib
import unittest
import uuid

from tools.cortex_verifier import NS_CORTEX, IndependentVerifier, Verdict, encode_cbe_standalone, sign_bytes

NODE_ID = uuid.uuid5(NS_CORTEX, "node:worker_01")


def generate_valid_evidence_bundle(steps: int = 3) -> dict:
    """Helper to generate a mathematically valid evidence bundle."""
    genesis_epoch = 0
    hasher_w0 = hashlib.sha256()
    hasher_w0.update(NS_CORTEX.bytes)
    hasher_w0.update(NODE_ID.bytes)
    hasher_w0.update(genesis_epoch.to_bytes(8, byteorder="big"))
    current_w = hasher_w0.digest()

    anchor = {"node_id": str(NODE_ID), "genesis_epoch": genesis_epoch, "expected_w0": current_w.hex()}

    intents = []
    tokens = []
    events = []
    witness_chain = []

    for seq in range(1, steps + 1):
        # 1. Intent
        intent_body = {"action": f"fs_op_{seq}", "path": f"/var/data/log_{seq}"}
        body_cbe = encode_cbe_standalone(intent_body)
        sig = sign_bytes(body_cbe).hex()
        intent = {"body": intent_body, "signature": sig}
        intents.append(intent)

        # 2. Token
        signed_intent_cbe = encode_cbe_standalone(intent)
        intent_hash = hashlib.sha256(signed_intent_cbe).hexdigest()
        token = {"intent_hash": intent_hash, "epoch": seq, "nonce": f"nonce_{seq}"}
        tokens.append(token)

        # 3. Event
        event = {"event": f"fs_op_{seq}_committed", "seq": seq}
        events.append(event)

        # 4. Witness Entry
        event_digest = hashlib.sha256(encode_cbe_standalone(event)).digest()
        intent_digest = hashlib.sha256(encode_cbe_standalone(intent)).digest()

        w_hasher = hashlib.sha256()
        w_hasher.update(current_w)
        w_hasher.update(event_digest)
        w_hasher.update(intent_digest)
        next_w = w_hasher.digest()

        timestamp_ns = 1700000000000000000 + seq
        signable_bytes = (
            bytes([1])
            + seq.to_bytes(8, byteorder="big")
            + timestamp_ns.to_bytes(8, byteorder="big")
            + current_w
            + event_digest
            + intent_digest
            + next_w
        )
        entry_sig = sign_bytes(signable_bytes).hex()

        entry = {
            "version": 1,
            "sequence": seq,
            "timestamp_ns": timestamp_ns,
            "prev_witness": current_w.hex(),
            "event_digest": event_digest.hex(),
            "intent_digest": intent_digest.hex(),
            "witness": next_w.hex(),
            "signature": entry_sig,
        }
        witness_chain.append(entry)
        current_w = next_w

    return {"anchor": anchor, "intents": intents, "tokens": tokens, "events": events, "witness_chain": witness_chain}


class TestGateJIndependentVerifier(unittest.TestCase):
    """Gate J Standalone Independent Verifier (P4) Test Harness."""

    def setUp(self):
        self.verifier = IndependentVerifier()

    def test_j_adv_001_valid_evidence_bundle(self):
        """J-ADV-001: Untampered valid evidence bundle evaluates to Verdict.VALID (0)."""
        bundle = generate_valid_evidence_bundle(steps=3)
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.VALID)
        self.assertIn("EVIDENCE_VERIFIED_VALID", msg)

    def test_j_adv_002_event_payload_mutation(self):
        """J-ADV-002: Event payload byte mutation triggers Verdict.INVALID (1)."""
        bundle = generate_valid_evidence_bundle(steps=3)
        bundle["events"][0]["event"] = "MUTATED_EVENT_PAYLOAD"
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_EVENT_DIGEST_MISMATCH", msg)

    def test_j_adv_003_intent_parameter_substitution(self):
        """J-ADV-003: SignedIntent parameter substitution triggers Verdict.INVALID (1)."""
        bundle = generate_valid_evidence_bundle(steps=3)
        bundle["intents"][0]["body"]["path"] = "/etc/shadow"
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_SIGNATURE_INVALID", msg)

    def test_j_adv_004_event_omission_traps(self):
        """J-ADV-004: Dropping step 2 triggers Verdict.INVALID (1)."""
        bundle = generate_valid_evidence_bundle(steps=3)
        bundle["events"].pop(1)
        bundle["intents"].pop(1)
        bundle["tokens"].pop(1)
        bundle["witness_chain"].pop(1)
        # Sequence in entry 2 will now be 3, expecting 2
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_SEQUENCE_GAP", msg)

    def test_j_adv_005_event_reordering_traps(self):
        """J-ADV-005: Swapping steps triggers Verdict.INVALID (1)."""
        bundle = generate_valid_evidence_bundle(steps=3)
        # Swap step 1 and step 2 in witness_chain
        bundle["witness_chain"][0], bundle["witness_chain"][1] = bundle["witness_chain"][1], bundle["witness_chain"][0]
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)

    def test_j_adv_006_forged_authority_signature(self):
        """J-ADV-006: Forged authority signature triggers Verdict.INVALID (1)."""
        bundle = generate_valid_evidence_bundle(steps=3)
        bundle["intents"][0]["signature"] = "0" * 64
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_SIGNATURE_INVALID", msg)

    def test_j_adv_007_untrusted_genesis_anchor(self):
        """J-ADV-007: Modified genesis anchor W_0 triggers Verdict.INVALID (1)."""
        bundle = generate_valid_evidence_bundle(steps=3)
        bundle["anchor"]["expected_w0"] = "f" * 64
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_UNTRUSTED_ANCHOR_MISMATCH", msg)

    def test_j_adv_008_forged_recomputed_witness_rewrite(self):
        """J-ADV-008: Forged witness chain rewrite disconnects from W_0 -> Verdict.INVALID (1)."""
        bundle = generate_valid_evidence_bundle(steps=3)
        bundle["witness_chain"][0]["prev_witness"] = "a" * 64
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_CHAIN_BROKEN", msg)

    def test_j_adv_009_truncated_log_stream(self):
        """J-ADV-009: Missing witness chain section triggers Verdict.INDETERMINATE (2)."""
        bundle = generate_valid_evidence_bundle(steps=3)
        del bundle["witness_chain"]
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INDETERMINATE)
        self.assertIn("TRAP_INCOMPLETE_TRACE", msg)

    def test_j_adv_010_stream_length_mismatch(self):
        """J-ADV-010: Forked / unequal stream length triggers Verdict.INDETERMINATE (2)."""
        bundle = generate_valid_evidence_bundle(steps=3)
        bundle["events"].pop()
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INDETERMINATE)
        self.assertIn("TRAP_INCOMPLETE_TRACE_STREAM_LENGTH_MISMATCH", msg)

    def test_j_adv_011_missing_anchor_schema(self):
        """J-ADV-011: Missing anchor triggers Verdict.INDETERMINATE (2)."""
        bundle = generate_valid_evidence_bundle(steps=3)
        del bundle["anchor"]
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INDETERMINATE)

    def test_j_adv_012_unbound_token_intent_mismatch(self):
        """J-ADV-012: Token intent_hash mismatch triggers Verdict.INVALID (1)."""
        bundle = generate_valid_evidence_bundle(steps=3)
        bundle["tokens"][0]["intent_hash"] = "e" * 64
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_TOKEN_PARITY_MISMATCH", msg)

    def test_j_adv_013_duplicate_sequence_incarnation(self):
        """J-ADV-013: Duplicate sequence number / non-monotonic sequence mutation triggers Verdict.INVALID (1)."""
        bundle = generate_valid_evidence_bundle(steps=3)
        bundle["witness_chain"][1]["sequence"] = 1  # Duplicate sequence 1 instead of 2
        verdict, msg = self.verifier.verify_evidence_bundle(bundle)
        self.assertEqual(verdict, Verdict.INVALID)
        self.assertIn("TRAP_SEQUENCE_GAP", msg)

    def test_j_adv_014_13_class_property_fuzzing_engine(self):
        """J-ADV-014: Gate J 13-Class Property-Based Fuzzing Engine (100 randomized mutation trials)."""
        import random

        rng = random.Random(42)  # Deterministic seed for reproducible fuzzing

        for trial in range(100):
            bundle = generate_valid_evidence_bundle(steps=3)
            mutation_class = rng.randint(1, 13)

            if mutation_class == 1:
                # Class 1: Valid baseline (must be VALID)
                verdict, _ = self.verifier.verify_evidence_bundle(bundle)
                self.assertEqual(verdict, Verdict.VALID, f"Trial {trial}: Baseline bundle failed")
            elif mutation_class == 2:
                # Class 2: Event payload mutation
                bundle["events"][0]["event"] = f"MUTATED_{trial}"
                verdict, _ = self.verifier.verify_evidence_bundle(bundle)
                self.assertEqual(verdict, Verdict.INVALID, f"Trial {trial}: Event mutation allowed")
            elif mutation_class == 3:
                # Class 3: Intent parameter substitution
                bundle["intents"][0]["body"]["path"] = f"/unauthorized/path_{trial}"
                verdict, _ = self.verifier.verify_evidence_bundle(bundle)
                self.assertEqual(verdict, Verdict.INVALID, f"Trial {trial}: Intent mutation allowed")
            elif mutation_class == 4:
                # Class 4: Event omission
                bundle["events"].pop(0)
                verdict, _ = self.verifier.verify_evidence_bundle(bundle)
                self.assertIn(verdict, (Verdict.INVALID, Verdict.INDETERMINATE), f"Trial {trial}: Omission allowed")
            elif mutation_class == 5:
                # Class 5: Event reordering
                bundle["events"].reverse()
                verdict, _ = self.verifier.verify_evidence_bundle(bundle)
                self.assertIn(verdict, (Verdict.INVALID, Verdict.INDETERMINATE), f"Trial {trial}: Reordering allowed")
            elif mutation_class == 6:
                # Class 6: Signature forgery
                bundle["intents"][0]["signature"] = "deadbeef" * 8
                verdict, _ = self.verifier.verify_evidence_bundle(bundle)
                self.assertEqual(verdict, Verdict.INVALID, f"Trial {trial}: Signature forgery allowed")
            elif mutation_class == 7:
                # Class 7: Anchor corruption
                bundle["anchor"]["expected_w0"] = "00" * 32
                verdict, _ = self.verifier.verify_evidence_bundle(bundle)
                self.assertEqual(verdict, Verdict.INVALID, f"Trial {trial}: Anchor corruption allowed")
            elif mutation_class == 8:
                # Class 8: Witness chain rewrite
                bundle["witness_chain"][0]["witness"] = "ff" * 32
                verdict, _ = self.verifier.verify_evidence_bundle(bundle)
                self.assertEqual(verdict, Verdict.INVALID, f"Trial {trial}: Witness rewrite allowed")
            elif mutation_class == 9:
                # Class 9: Truncated stream
                del bundle["witness_chain"]
                verdict, _ = self.verifier.verify_evidence_bundle(bundle)
                self.assertEqual(verdict, Verdict.INDETERMINATE, f"Trial {trial}: Truncated stream allowed")
            elif mutation_class == 10:
                # Class 10: Stream length mismatch
                bundle["tokens"].pop()
                verdict, _ = self.verifier.verify_evidence_bundle(bundle)
                self.assertEqual(verdict, Verdict.INDETERMINATE, f"Trial {trial}: Stream length mismatch allowed")
            elif mutation_class == 11:
                # Class 11: Missing anchor
                del bundle["anchor"]
                verdict, _ = self.verifier.verify_evidence_bundle(bundle)
                self.assertEqual(verdict, Verdict.INDETERMINATE, f"Trial {trial}: Missing anchor allowed")
            elif mutation_class == 12:
                # Class 12: Token parity mismatch
                bundle["tokens"][0]["intent_hash"] = "1234" * 16
                verdict, _ = self.verifier.verify_evidence_bundle(bundle)
                self.assertEqual(verdict, Verdict.INVALID, f"Trial {trial}: Token parity mismatch allowed")
            elif mutation_class == 13:
                # Class 13: Non-monotonic sequence
                bundle["witness_chain"][1]["sequence"] = 99
                verdict, _ = self.verifier.verify_evidence_bundle(bundle)
                self.assertEqual(verdict, Verdict.INVALID, f"Trial {trial}: Non-monotonic sequence allowed")


if __name__ == "__main__":
    unittest.main()

