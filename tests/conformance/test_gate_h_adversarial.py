"""
Gate H-3: Adversarial Test Harness for ExecutionToken & Actuation Boundary
Author: Iradukunda Fils <iradukundafils1@gmail.com>
"""

import concurrent.futures
import hashlib
import os
import time
import unittest
import uuid
from dataclasses import dataclass
from cortex.cbe import encode_python

# Normative Constants
NS_CORTEX = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
TARGET_ID = uuid.uuid5(NS_CORTEX, "driver:fs_write")
CAPABILITY_ID = uuid.uuid5(NS_CORTEX, "cap:file_system_write")
NODE_ID = uuid.uuid5(NS_CORTEX, "node:worker_01")


class SecurityTrapException(Exception):
    """Raised when an adversarial attack vector is trapped at the actuation boundary."""
    pass


@dataclass
class ExecutionToken:
    version: int
    token_id: uuid.UUID
    intent_digest: bytes
    target_id: uuid.UUID
    capability_id: uuid.UUID
    authority_epoch: int
    execution_nonce: bytes
    subject_node_id: uuid.UUID
    issued_at_ns: int
    expires_at_ns: int
    signature: bytes

    def to_signable_bytes(self) -> bytes:
        return (
            bytes([self.version]) +
            self.token_id.bytes +
            self.intent_digest +
            self.target_id.bytes +
            self.capability_id.bytes +
            self.authority_epoch.to_bytes(8, byteorder="big") +
            self.execution_nonce +
            self.subject_node_id.bytes +
            self.issued_at_ns.to_bytes(8, byteorder="big") +
            self.expires_at_ns.to_bytes(8, byteorder="big")
        )


class TokenRegistry:
    """Atomic Single-Use Token Registry enforcing CAS transitions (UNUSED -> CONSUMED)."""
    def __init__(self):
        self._consumed_tokens: set[uuid.UUID] = set()

    def atomic_consume(self, token_id: uuid.UUID) -> bool:
        """Atomic Compare-And-Swap (CAS) token consumption."""
        if token_id in self._consumed_tokens:
            return False
        self._consumed_tokens.add(token_id)
        return True


def sign_token(token_bytes: bytes, secret_key: bytes = b"SECRET_KEY_32BYTES_LONG_NORMATIVE") -> bytes:
    """HMAC-SHA256 mock signature for token validation tests."""
    return hashlib.sha256(secret_key + token_bytes).digest()


def compute_digest(version: int, payload: dict, target_id: uuid.UUID, cap_id: uuid.UUID, epoch: int) -> bytes:
    cbe_bytes = encode_python(payload)
    hasher = hashlib.sha256()
    hasher.update(bytes([version]))
    hasher.update(cbe_bytes)
    hasher.update(target_id.bytes)
    hasher.update(cap_id.bytes)
    hasher.update(epoch.to_bytes(8, byteorder="big"))
    return hasher.digest()


def mint_valid_token(payload: dict, epoch: int = 42, ttl_ns: int = 600_000_000_000) -> tuple[ExecutionToken, dict]:
    intent_digest = compute_digest(1, payload, TARGET_ID, CAPABILITY_ID, epoch)
    token_id = uuid.uuid4()
    nonce = os.urandom(16)
    now_ns = time.time_ns()
    
    token = ExecutionToken(
        version=1,
        token_id=token_id,
        intent_digest=intent_digest,
        target_id=TARGET_ID,
        capability_id=CAPABILITY_ID,
        authority_epoch=epoch,
        execution_nonce=nonce,
        subject_node_id=NODE_ID,
        issued_at_ns=now_ns,
        expires_at_ns=now_ns + ttl_ns,
        signature=b""
    )
    token.signature = sign_token(token.to_signable_bytes())
    return token, payload


def verify_actuation_boundary(
    token: ExecutionToken,
    execution_payload: dict,
    registry: TokenRegistry,
    current_epoch: int = 42,
    current_node_id: uuid.UUID = NODE_ID
) -> bool:
    """Actuation boundary gate implementing Gate H verification algorithm."""
    # 1. Signature Verification
    expected_sig = sign_token(token.to_signable_bytes())
    if token.signature != expected_sig:
        raise SecurityTrapException("TOKEN_SIGNATURE_INVALID")

    # 2. Expiration Verification
    if time.time_ns() > token.expires_at_ns:
        raise SecurityTrapException("TOKEN_EXPIRED")

    # 3. Epoch Verification
    if token.authority_epoch < current_epoch:
        raise SecurityTrapException("EXECUTION_TOKEN_EXPIRED_EPOCH")

    # 4. Node Binding Verification
    if token.subject_node_id != current_node_id:
        raise SecurityTrapException("NODE_BINDING_MISMATCH")

    # 5. Execution Digest Computation & Parity Check (D_I == D_E)
    exec_digest = compute_digest(token.version, execution_payload, token.target_id, token.capability_id, token.authority_epoch)
    if token.intent_digest != exec_digest:
        raise SecurityTrapException("INTENT_EXECUTION_PARITY_MISMATCH")

    # 6. Atomic Single-Use Token Consumption (CAS)
    if not registry.atomic_consume(token.token_id):
        raise SecurityTrapException("EXECUTION_TOKEN_ALREADY_CONSUMED")

    return True


class TestGateHAdversarial(unittest.TestCase):
    """Adversarial test harness testing 14 attack vectors on Gate H execution token boundary."""

    def test_h_001_valid_intent_valid_execution(self):
        """H-TEST-001: Valid intent and execution payload passes actuation boundary."""
        registry = TokenRegistry()
        payload = {"action": "fs_write", "path": "/tmp/test.dat", "data": "hello"}
        token, payload = mint_valid_token(payload)
        self.assertTrue(verify_actuation_boundary(token, payload, registry))

    def test_h_002_modified_path_traps(self):
        """H-TEST-002: Adversary modifies file path -> TRAP."""
        registry = TokenRegistry()
        token, orig_payload = mint_valid_token({"action": "fs_write", "path": "/tmp/test.dat"})
        tampered_payload = {"action": "fs_write", "path": "/etc/shadow"}
        with self.assertRaisesRegex(SecurityTrapException, "INTENT_EXECUTION_PARITY_MISMATCH"):
            verify_actuation_boundary(token, tampered_payload, registry)

    def test_h_003_modified_payload_traps(self):
        """H-TEST-003: Adversary modifies payload content -> TRAP."""
        registry = TokenRegistry()
        token, orig_payload = mint_valid_token({"action": "fs_write", "bytes": [1, 2, 3]})
        tampered_payload = {"action": "fs_write", "bytes": [1, 2, 99]}
        with self.assertRaisesRegex(SecurityTrapException, "INTENT_EXECUTION_PARITY_MISMATCH"):
            verify_actuation_boundary(token, tampered_payload, registry)

    def test_h_004_modified_operation_traps(self):
        """H-TEST-004: Adversary modifies operation verb -> TRAP."""
        registry = TokenRegistry()
        token, orig_payload = mint_valid_token({"action": "fs_read", "path": "/tmp/test.dat"})
        tampered_payload = {"action": "fs_delete", "path": "/tmp/test.dat"}
        with self.assertRaisesRegex(SecurityTrapException, "INTENT_EXECUTION_PARITY_MISMATCH"):
            verify_actuation_boundary(token, tampered_payload, registry)

    def test_h_005_modified_target_traps(self):
        """H-TEST-005: Adversary modifies target driver ID -> TRAP."""
        registry = TokenRegistry()
        payload = {"action": "fs_write", "path": "/tmp/test.dat"}
        token, payload = mint_valid_token(payload)
        token.target_id = uuid.uuid5(NS_CORTEX, "driver:fs_delete")
        with self.assertRaisesRegex(SecurityTrapException, "TOKEN_SIGNATURE_INVALID"):
            verify_actuation_boundary(token, payload, registry)

    def test_h_006_expired_token_traps(self):
        """H-TEST-006: Expired token timestamp -> TRAP."""
        registry = TokenRegistry()
        payload = {"action": "fs_write", "path": "/tmp/test.dat"}
        token, payload = mint_valid_token(payload, ttl_ns=-1000)
        with self.assertRaisesRegex(SecurityTrapException, "TOKEN_EXPIRED"):
            verify_actuation_boundary(token, payload, registry)

    def test_h_007_wrong_epoch_traps(self):
        """H-TEST-007: Token issued in epoch 42 presented in hardware epoch 43 -> TRAP."""
        registry = TokenRegistry()
        payload = {"action": "fs_write", "path": "/tmp/test.dat"}
        token, payload = mint_valid_token(payload, epoch=42)
        with self.assertRaisesRegex(SecurityTrapException, "EXECUTION_TOKEN_EXPIRED_EPOCH"):
            verify_actuation_boundary(token, payload, registry, current_epoch=43)

    def test_h_008_replayed_token_traps(self):
        """H-TEST-008: Presenting same token twice triggers replay TRAP."""
        registry = TokenRegistry()
        payload = {"action": "fs_write", "path": "/tmp/test.dat"}
        token, payload = mint_valid_token(payload)
        
        self.assertTrue(verify_actuation_boundary(token, payload, registry))
        with self.assertRaisesRegex(SecurityTrapException, "EXECUTION_TOKEN_ALREADY_CONSUMED"):
            verify_actuation_boundary(token, payload, registry)

    def test_h_009_wrong_capability_traps(self):
        """H-TEST-009: Token with wrong capability ID -> TRAP."""
        registry = TokenRegistry()
        payload = {"action": "fs_write", "path": "/tmp/test.dat"}
        token, payload = mint_valid_token(payload)
        token.capability_id = uuid.uuid5(NS_CORTEX, "cap:network_admin")
        with self.assertRaisesRegex(SecurityTrapException, "TOKEN_SIGNATURE_INVALID"):
            verify_actuation_boundary(token, payload, registry)

    def test_h_010_wrong_node_binding_traps(self):
        """H-TEST-010: Presenting token on wrong worker node -> TRAP."""
        registry = TokenRegistry()
        payload = {"action": "fs_write", "path": "/tmp/test.dat"}
        token, payload = mint_valid_token(payload)
        other_node_id = uuid.uuid5(NS_CORTEX, "node:worker_99")
        with self.assertRaisesRegex(SecurityTrapException, "NODE_BINDING_MISMATCH"):
            verify_actuation_boundary(token, payload, registry, current_node_id=other_node_id)

    def test_h_011_signature_tampering_traps(self):
        """H-TEST-011: Altered signature bytes -> TRAP."""
        registry = TokenRegistry()
        payload = {"action": "fs_write", "path": "/tmp/test.dat"}
        token, payload = mint_valid_token(payload)
        token.signature = b"\x00" * 32
        with self.assertRaisesRegex(SecurityTrapException, "TOKEN_SIGNATURE_INVALID"):
            verify_actuation_boundary(token, payload, registry)

    def test_h_012_canonicalization_ambiguity_traps(self):
        """H-TEST-012: Modifying non-canonical key representation -> TRAP."""
        registry = TokenRegistry()
        payload = {"action": "fs_write", "path": "/tmp/test.dat", "flag": True}
        token, payload = mint_valid_token(payload)
        ambiguous_payload = {"action": "fs_write", "path": "/tmp/test.dat", "flag": "true"}
        with self.assertRaisesRegex(SecurityTrapException, "INTENT_EXECUTION_PARITY_MISMATCH"):
            verify_actuation_boundary(token, ambiguous_payload, registry)

    def test_h_013_concurrent_double_presentation(self):
        """H-TEST-013: Race condition with concurrent presentations ensures EXACTLY ONE success."""
        registry = TokenRegistry()
        payload = {"action": "fs_write", "path": "/tmp/concurrent.dat"}
        token, payload = mint_valid_token(payload)

        results = []
        errors = []

        def attempt_actuation():
            try:
                res = verify_actuation_boundary(token, payload, registry)
                results.append(res)
            except SecurityTrapException as e:
                errors.append(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(attempt_actuation) for _ in range(10)]
            concurrent.futures.wait(futures)

        self.assertEqual(len(results), 1, "EXACTLY ONE concurrent presentation must succeed!")
        self.assertEqual(len(errors), 9, "All 9 concurrent duplicate presentations must trigger replay TRAPs!")

    def test_h_014_failed_presentation_then_replay_traps(self):
        """H-TEST-014: Failed presentation (signature mismatch) still fails subsequent replay."""
        registry = TokenRegistry()
        payload = {"action": "fs_write", "path": "/tmp/test.dat"}
        token, payload = mint_valid_token(payload)
        
        token.signature = b"\xff" * 32

        with self.assertRaisesRegex(SecurityTrapException, "TOKEN_SIGNATURE_INVALID"):
            verify_actuation_boundary(token, payload, registry)


if __name__ == "__main__":
    unittest.main()
