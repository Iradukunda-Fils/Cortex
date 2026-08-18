"""
Gate H-2: Canonicalization & Intent Digest Test Suite
Author: Iradukunda Fils <iradukundafils1@gmail.com>
"""

import hashlib
import unittest
import uuid
from cortex.cbe import encode_python

# Normative Namespace Constants
NS_CORTEX = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
TARGET_ID = uuid.uuid5(NS_CORTEX, "driver:fs_write")
CAPABILITY_ID = uuid.uuid5(NS_CORTEX, "cap:file_system_write")


def compute_intent_digest(version: int, payload: dict, target_id: uuid.UUID, cap_id: uuid.UUID, epoch: int) -> bytes:
    """Compute normative IntentDigest (D_I) over payload using Cortex-CBE."""
    cbe_bytes = encode_python(payload)
    hasher = hashlib.sha256()
    hasher.update(bytes([version]))
    hasher.update(cbe_bytes)
    hasher.update(target_id.bytes)
    hasher.update(cap_id.bytes)
    hasher.update(epoch.to_bytes(8, byteorder="big"))
    return hasher.digest()


class TestGateHCanonicalization(unittest.TestCase):
    """Test suite asserting deterministic CBE canonicalization and intent digest immutability."""

    def test_canonicalization_identical_semantic_objects(self):
        """Verify identical semantic payloads with different key orders produce identical digests."""
        payload_a = {"action": "fs_write", "path": "/var/log/system.log", "bytes": [74, 137, 24]}
        payload_b = {"bytes": [74, 137, 24], "path": "/var/log/system.log", "action": "fs_write"}

        digest_a = compute_intent_digest(1, payload_a, TARGET_ID, CAPABILITY_ID, epoch=42)
        digest_b = compute_intent_digest(1, payload_b, TARGET_ID, CAPABILITY_ID, epoch=42)

        self.assertEqual(digest_a, digest_b, "Identical semantic objects MUST produce identical CBE digests!")

    def test_canonicalization_path_modification_digest(self):
        """Verify modifying a path by a single character alters the digest."""
        payload_base = {"action": "fs_write", "path": "/var/log/system.log"}
        payload_modified = {"action": "fs_write", "path": "/var/log/system.txt"}

        digest_base = compute_intent_digest(1, payload_base, TARGET_ID, CAPABILITY_ID, epoch=42)
        digest_mod = compute_intent_digest(1, payload_modified, TARGET_ID, CAPABILITY_ID, epoch=42)

        self.assertNotEqual(digest_base, digest_mod, "Path modification MUST alter the intent digest!")

    def test_canonicalization_payload_modification_digest(self):
        """Verify modifying payload bytes alters the digest."""
        payload_base = {"action": "fs_write", "bytes": [1, 2, 3]}
        payload_mod = {"action": "fs_write", "bytes": [1, 2, 4]}

        digest_base = compute_intent_digest(1, payload_base, TARGET_ID, CAPABILITY_ID, epoch=42)
        digest_mod = compute_intent_digest(1, payload_mod, TARGET_ID, CAPABILITY_ID, epoch=42)

        self.assertNotEqual(digest_base, digest_mod, "Payload byte modification MUST alter the intent digest!")

    def test_canonicalization_target_modification_digest(self):
        """Verify modifying the target driver ID alters the digest."""
        payload = {"action": "fs_write", "path": "/data"}
        alt_target_id = uuid.uuid5(NS_CORTEX, "driver:fs_read")

        digest_base = compute_intent_digest(1, payload, TARGET_ID, CAPABILITY_ID, epoch=42)
        digest_alt = compute_intent_digest(1, payload, alt_target_id, CAPABILITY_ID, epoch=42)

        self.assertNotEqual(digest_base, digest_alt, "Target driver ID modification MUST alter the digest!")

    def test_canonicalization_epoch_modification_digest(self):
        """Verify modifying authority epoch alters the digest."""
        payload = {"action": "fs_write", "path": "/data"}

        digest_epoch_42 = compute_intent_digest(1, payload, TARGET_ID, CAPABILITY_ID, epoch=42)
        digest_epoch_43 = compute_intent_digest(1, payload, TARGET_ID, CAPABILITY_ID, epoch=43)

        self.assertNotEqual(digest_epoch_42, digest_epoch_43, "Authority epoch modification MUST alter the digest!")


if __name__ == "__main__":
    unittest.main()
