"""
Gate I: Cryptographic Causal Witness Chain (P3) Test Suite
Author: Iradukunda Fils <iradukundafils1@gmail.com>
"""

import hashlib
import time
import unittest
import uuid
from dataclasses import dataclass

from cortex.cbe import encode_python

# Normative Constants
NS_CORTEX = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
NODE_ID = uuid.uuid5(NS_CORTEX, "node:worker_01")


class WitnessTrapException(Exception):
    """Raised when an adversarial state or witness chain attack is detected."""

    pass


def sign_bytes(data: bytes, secret_key: bytes = b"WITNESS_SECRET_KEY_32BYTES_LONG_") -> bytes:
    """HMAC-SHA256 mock signature for witness entry verification."""
    return hashlib.sha256(secret_key + data).digest()


@dataclass
class WitnessEntry:
    version: int
    sequence: int
    timestamp_ns: int
    prev_witness: bytes
    event_digest: bytes
    intent_digest: bytes
    witness: bytes
    signature: bytes

    def to_signable_bytes(self) -> bytes:
        return (
            bytes([self.version])
            + self.sequence.to_bytes(8, byteorder="big")
            + self.timestamp_ns.to_bytes(8, byteorder="big")
            + self.prev_witness
            + self.event_digest
            + self.intent_digest
            + self.witness
        )


class RollingWitnessChain:
    """Append-only rolling cryptographic witness chain implementation."""

    def __init__(self, node_id: uuid.UUID = NODE_ID, genesis_epoch: int = 0):
        self.node_id = node_id
        self.genesis_epoch = genesis_epoch
        self.sequence = 0

        # Genesis witness W_0
        hasher = hashlib.sha256()
        hasher.update(NS_CORTEX.bytes)
        hasher.update(node_id.bytes)
        hasher.update(genesis_epoch.to_bytes(8, byteorder="big"))
        self.current_witness = hasher.digest()

        self.chain: list[WitnessEntry] = []

    def append_transition(self, event_payload: dict, intent_payload: dict) -> WitnessEntry:
        """Appends a new state transition (t -> t+1) to the rolling witness chain."""
        self.sequence += 1
        now_ns = time.time_ns()

        event_cbe = encode_python(event_payload)
        intent_cbe = encode_python(intent_payload)

        event_digest = hashlib.sha256(event_cbe).digest()
        intent_digest = hashlib.sha256(intent_cbe).digest()

        # W_{t+1} = SHA256( W_t || D_E || D_I )
        hasher = hashlib.sha256()
        hasher.update(self.current_witness)
        hasher.update(event_digest)
        hasher.update(intent_digest)
        next_witness = hasher.digest()

        entry = WitnessEntry(
            version=1,
            sequence=self.sequence,
            timestamp_ns=now_ns,
            prev_witness=self.current_witness,
            event_digest=event_digest,
            intent_digest=intent_digest,
            witness=next_witness,
            signature=b"",
        )
        entry.signature = sign_bytes(entry.to_signable_bytes())

        self.current_witness = next_witness
        self.chain.append(entry)
        return entry


def verify_witness_chain(chain: list[WitnessEntry], node_id: uuid.UUID = NODE_ID, genesis_epoch: int = 0) -> bool:
    """Independently verifies a rolling witness chain's cryptographic integrity."""
    if not chain:
        return True

    # Assert Genesis State W_0
    hasher = hashlib.sha256()
    hasher.update(NS_CORTEX.bytes)
    hasher.update(node_id.bytes)
    hasher.update(genesis_epoch.to_bytes(8, byteorder="big"))
    expected_prev = hasher.digest()

    for idx, entry in enumerate(chain):
        # 1. Signature Check
        expected_sig = sign_bytes(entry.to_signable_bytes())
        if entry.signature != expected_sig:
            raise WitnessTrapException("TRAP_WITNESS_SIGNATURE_INVALID")

        # 2. Sequence Monotonicity
        if entry.sequence != idx + 1:
            raise WitnessTrapException("TRAP_WITNESS_SEQUENCE_BREAK")

        # 3. Chain Continuity (prev_witness == W_t)
        if entry.prev_witness != expected_prev:
            raise WitnessTrapException("TRAP_WITNESS_CHAIN_BROKEN")

        # 4. Rolling Witness Hash Derivation Assertion: W_{t+1} == SHA256(W_t || D_E || D_I)
        w_hasher = hashlib.sha256()
        w_hasher.update(entry.prev_witness)
        w_hasher.update(entry.event_digest)
        w_hasher.update(entry.intent_digest)
        computed_witness = w_hasher.digest()

        if entry.witness != computed_witness:
            raise WitnessTrapException("TRAP_WITNESS_DIGEST_MISMATCH")

        expected_prev = entry.witness

    return True


class TestGateICausalWitness(unittest.TestCase):
    """Gate I Causal Witness Chain (P3) Test Suite."""

    def test_i_001_valid_witness_chain(self):
        """I-TEST-001: Append valid transitions and verify witness chain passes."""
        chain_engine = RollingWitnessChain()
        chain_engine.append_transition({"event": "fs_write_start", "bytes": 100}, {"action": "fs_write"})
        chain_engine.append_transition({"event": "fs_write_commit", "status": "OK"}, {"action": "fs_write"})
        chain_engine.append_transition({"event": "audit_log_updated"}, {"action": "audit"})

        self.assertTrue(verify_witness_chain(chain_engine.chain))

    def test_i_002_event_payload_tampering_traps(self):
        """I-TEST-002: Tampering an event digest causes witness mismatch TRAP."""
        chain_engine = RollingWitnessChain()
        entry1 = chain_engine.append_transition({"event": "start"}, {"action": "op"})

        # Tamper event_digest
        tampered_entry = WitnessEntry(
            version=entry1.version,
            sequence=entry1.sequence,
            timestamp_ns=entry1.timestamp_ns,
            prev_witness=entry1.prev_witness,
            event_digest=hashlib.sha256(b"TAMPERED_EVENT").digest(),
            intent_digest=entry1.intent_digest,
            witness=entry1.witness,
            signature=entry1.signature,
        )
        # Update signature for sign check so digest check fails
        tampered_entry.signature = sign_bytes(tampered_entry.to_signable_bytes())

        with self.assertRaisesRegex(WitnessTrapException, "TRAP_WITNESS_DIGEST_MISMATCH"):
            verify_witness_chain([tampered_entry])

    def test_i_003_intent_payload_tampering_traps(self):
        """I-TEST-003: Tampering intent digest causes witness mismatch TRAP."""
        chain_engine = RollingWitnessChain()
        entry1 = chain_engine.append_transition({"event": "start"}, {"action": "op"})

        tampered_entry = WitnessEntry(
            version=entry1.version,
            sequence=entry1.sequence,
            timestamp_ns=entry1.timestamp_ns,
            prev_witness=entry1.prev_witness,
            event_digest=entry1.event_digest,
            intent_digest=hashlib.sha256(b"TAMPERED_INTENT").digest(),
            witness=entry1.witness,
            signature=entry1.signature,
        )
        tampered_entry.signature = sign_bytes(tampered_entry.to_signable_bytes())

        with self.assertRaisesRegex(WitnessTrapException, "TRAP_WITNESS_DIGEST_MISMATCH"):
            verify_witness_chain([tampered_entry])

    def test_i_004_event_omission_traps(self):
        """I-TEST-004: Omitting an entry in the chain breaks sequence and prev_witness linkage."""
        chain_engine = RollingWitnessChain()
        e1 = chain_engine.append_transition({"event": "step1"}, {"action": "op1"})
        _ = chain_engine.append_transition({"event": "step2"}, {"action": "op2"})
        e3 = chain_engine.append_transition({"event": "step3"}, {"action": "op3"})

        # Omit step 2 -> [e1, e3]
        broken_chain = [e1, e3]

        with self.assertRaisesRegex(WitnessTrapException, "(TRAP_WITNESS_SEQUENCE_BREAK|TRAP_WITNESS_CHAIN_BROKEN)"):
            verify_witness_chain(broken_chain)

    def test_i_005_event_reordering_traps(self):
        """I-TEST-005: Swapping two events breaks parent witness linkage."""
        chain_engine = RollingWitnessChain()
        e1 = chain_engine.append_transition({"event": "step1"}, {"action": "op1"})
        e2 = chain_engine.append_transition({"event": "step2"}, {"action": "op2"})

        # Swap e1 and e2 -> [e2, e1]
        swapped_chain = [e2, e1]

        with self.assertRaisesRegex(WitnessTrapException, "(TRAP_WITNESS_SEQUENCE_BREAK|TRAP_WITNESS_CHAIN_BROKEN)"):
            verify_witness_chain(swapped_chain)

    def test_i_006_signature_tampering_traps(self):
        """I-TEST-006: Modifying signature bytes triggers signature invalid TRAP."""
        chain_engine = RollingWitnessChain()
        e1 = chain_engine.append_transition({"event": "step1"}, {"action": "op1"})
        e1.signature = b"\x00" * 32

        with self.assertRaisesRegex(WitnessTrapException, "TRAP_WITNESS_SIGNATURE_INVALID"):
            verify_witness_chain([e1])

    def test_i_007_genesis_state_tampering_traps(self):
        """I-TEST-007: Valid chain presented against wrong node genesis ID fails."""
        chain_engine = RollingWitnessChain(node_id=NODE_ID)
        chain_engine.append_transition({"event": "step1"}, {"action": "op1"})

        other_node_id = uuid.uuid5(NS_CORTEX, "node:worker_99")
        with self.assertRaisesRegex(WitnessTrapException, "TRAP_WITNESS_CHAIN_BROKEN"):
            verify_witness_chain(chain_engine.chain, node_id=other_node_id)


if __name__ == "__main__":
    unittest.main()
