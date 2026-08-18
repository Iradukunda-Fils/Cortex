#!/usr/bin/env python3
"""
Standalone Untrusted Independent Verifier Engine (Gate J / P4)
Author: Iradukunda Fils <iradukundafils1@gmail.com>

Zero Substrate Dependencies: Built using standard Python library primitives only.
Does NOT import cortex runtime, event store, or emulator modules.
"""

import enum
import hashlib
import json
import sys
import uuid

# Normative Constants
NS_CORTEX = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
SECRET_KEY = b"WITNESS_SECRET_KEY_32BYTES_LONG_"


class Verdict(enum.IntEnum):
    VALID = 0
    INVALID = 1
    INDETERMINATE = 2


def sign_bytes(data: bytes, secret_key: bytes = SECRET_KEY) -> bytes:
    """HMAC-SHA256 mock signature for standalone verification."""
    return hashlib.sha256(secret_key + data).digest()


def encode_cbe_standalone(val) -> bytes:
    """Zero-dependency deterministic Canonical Binary Encoding (CBE) helper."""
    if val is None:
        return b"\x00"
    elif isinstance(val, bool):
        return b"\x01" if val else b"\x02"
    elif isinstance(val, int):
        return b"\x03" + val.to_bytes(8, byteorder="big", signed=True)
    elif isinstance(val, str):
        buf = val.encode("utf-8")
        return b"\x04" + len(buf).to_bytes(4, byteorder="big") + buf
    elif isinstance(val, bytes):
        return b"\x05" + len(val).to_bytes(4, byteorder="big") + val
    elif isinstance(val, list):
        out = b"\x06" + len(val).to_bytes(4, byteorder="big")
        for item in val:
            out += encode_cbe_standalone(item)
        return out
    elif isinstance(val, dict):
        # Lexicographically sorted key pairs
        sorted_keys = sorted(val.keys())
        out = b"\x07" + len(sorted_keys).to_bytes(4, byteorder="big")
        for k in sorted_keys:
            k_bytes = k.encode("utf-8")
            out += len(k_bytes).to_bytes(4, byteorder="big") + k_bytes
            out += encode_cbe_standalone(val[k])
        return out
    else:
        raise ValueError(f"Unsupported CBE type: {type(val)}")


class IndependentVerifier:
    """Zero-dependency evidence verification engine."""

    def verify_evidence_bundle(self, bundle: dict) -> tuple[Verdict, str]:
        """
        Verifies an untrusted evidence bundle.
        Returns tuple of (Verdict, detailed_message).
        """
        # Validate Bundle Composition
        if not isinstance(bundle, dict):
            return Verdict.INVALID, "TRAP_MALFORMED_BUNDLE_SCHEMA"

        required_sections = ["anchor", "intents", "tokens", "events", "witness_chain"]
        for section in required_sections:
            if section not in bundle:
                return Verdict.INDETERMINATE, f"TRAP_INCOMPLETE_TRACE_MISSING_{section.upper()}"

        anchor = bundle["anchor"]
        intents = bundle["intents"]
        tokens = bundle["tokens"]
        events = bundle["events"]
        witness_chain = bundle["witness_chain"]

        # Check for Truncated / Empty Evidence Streams
        if not witness_chain or not events or not intents:
            return Verdict.INDETERMINATE, "TRAP_INCOMPLETE_TRACE_EMPTY_STREAM"

        if len(witness_chain) != len(events) or len(events) != len(intents):
            return Verdict.INDETERMINATE, "TRAP_INCOMPLETE_TRACE_STREAM_LENGTH_MISMATCH"

        # 1. Genesis Anchor Verification W_0
        try:
            node_id = uuid.UUID(anchor.get("node_id", ""))
            genesis_epoch = int(anchor.get("genesis_epoch", 0))
        except (ValueError, TypeError):
            return Verdict.INVALID, "TRAP_UNTRUSTED_ANCHOR_MALFORMED"

        hasher_w0 = hashlib.sha256()
        hasher_w0.update(NS_CORTEX.bytes)
        hasher_w0.update(node_id.bytes)
        hasher_w0.update(genesis_epoch.to_bytes(8, byteorder="big"))
        expected_prev_witness = hasher_w0.digest()

        # Check explicit anchor match if provided
        anchor_w0_hex = anchor.get("expected_w0", "")
        if anchor_w0_hex and bytes.fromhex(anchor_w0_hex) != expected_prev_witness:
            return Verdict.INVALID, "TRAP_UNTRUSTED_ANCHOR_MISMATCH"

        # 2. Sequential Event-Intent-Witness Verification Loop
        for idx, entry in enumerate(witness_chain):
            intent = intents[idx]
            token = tokens[idx] if idx < len(tokens) else None
            event = events[idx]

            # A. SignedIntent Signature Validation
            intent_sig_hex = intent.get("signature", "")
            intent_body = intent.get("body", {})
            intent_body_cbe = encode_cbe_standalone(intent_body)
            expected_intent_sig = sign_bytes(intent_body_cbe)

            if not intent_sig_hex or bytes.fromhex(intent_sig_hex) != expected_intent_sig:
                return Verdict.INVALID, f"TRAP_SIGNATURE_INVALID_AT_STEP_{idx+1}"

            # B. ExecutionToken Parity Assertion D_3 == D_2
            if token:
                signed_intent_cbe = encode_cbe_standalone(intent)
                expected_token_intent_hash = hashlib.sha256(signed_intent_cbe).hexdigest()
                actual_token_hash = token.get("intent_hash", "")
                if actual_token_hash != expected_token_intent_hash:
                    return Verdict.INVALID, f"TRAP_TOKEN_PARITY_MISMATCH_AT_STEP_{idx+1}"

            # C. Sequence Monotonicity Check
            seq = entry.get("sequence", 0)
            if seq != idx + 1:
                return Verdict.INVALID, f"TRAP_SEQUENCE_GAP_AT_STEP_{idx+1}"

            # D. Chain Continuity Assertion prev_witness == W_t
            entry_prev_w_hex = entry.get("prev_witness", "")
            if bytes.fromhex(entry_prev_w_hex) != expected_prev_witness:
                return Verdict.INVALID, f"TRAP_CHAIN_BROKEN_AT_STEP_{idx+1}"

            # E. Digest Re-computation & Rolling Witness Assertion W_{t+1}
            event_cbe = encode_cbe_standalone(event)
            actual_event_digest = hashlib.sha256(event_cbe).digest()
            if entry.get("event_digest", "") != actual_event_digest.hex():
                return Verdict.INVALID, f"TRAP_EVENT_DIGEST_MISMATCH_AT_STEP_{idx+1}"

            intent_cbe = encode_cbe_standalone(intent)
            actual_intent_digest = hashlib.sha256(intent_cbe).digest()
            if entry.get("intent_digest", "") != actual_intent_digest.hex():
                return Verdict.INVALID, f"TRAP_INTENT_DIGEST_MISMATCH_AT_STEP_{idx+1}"

            # Recompute W_{t+1} = SHA256( W_t || D_E || D_I )
            w_hasher = hashlib.sha256()
            w_hasher.update(expected_prev_witness)
            w_hasher.update(actual_event_digest)
            w_hasher.update(actual_intent_digest)
            computed_witness = w_hasher.digest()

            if entry.get("witness", "") != computed_witness.hex():
                return Verdict.INVALID, f"TRAP_WITNESS_REWRITE_MISMATCH_AT_STEP_{idx+1}"

            # F. Entry Signature Validation
            signable_bytes = (
                bytes([entry.get("version", 1)]) +
                seq.to_bytes(8, byteorder="big") +
                int(entry.get("timestamp_ns", 0)).to_bytes(8, byteorder="big") +
                bytes.fromhex(entry_prev_w_hex) +
                actual_event_digest +
                actual_intent_digest +
                computed_witness
            )
            expected_entry_sig = sign_bytes(signable_bytes)
            if entry.get("signature", "") != expected_entry_sig.hex():
                return Verdict.INVALID, f"TRAP_WITNESS_ENTRY_SIGNATURE_INVALID_AT_STEP_{idx+1}"

            # Update expected prev witness for step t+1
            expected_prev_witness = computed_witness

        # Terminal status assertion (Check if incomplete/truncated)
        if bundle.get("is_incomplete", False):
            return Verdict.INDETERMINATE, "TRAP_INCOMPLETE_TRACE_FLAGGED"

        return Verdict.VALID, "EVIDENCE_VERIFIED_VALID"


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 cortex_verifier.py <path_to_evidence_bundle.json>")
        sys.exit(int(Verdict.INDETERMINATE))

    evidence_path = sys.argv[1]
    try:
        with open(evidence_path, "r", encoding="utf-8") as f:
            bundle_data = json.load(f)
    except Exception as e:
        print(f"VERDICT: INDETERMINATE - File read error: {e}")
        sys.exit(int(Verdict.INDETERMINATE))

    verifier = IndependentVerifier()
    verdict, msg = verifier.verify_evidence_bundle(bundle_data)
    print(f"VERDICT: {verdict.name} ({int(verdict)}) - {msg}")
    sys.exit(int(verdict))


if __name__ == "__main__":
    main()
