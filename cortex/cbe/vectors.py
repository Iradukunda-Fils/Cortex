"""
Cortex Test Vectors & Deterministic UUIDv5 Raw-Byte Lineage Derivation
"""

import hashlib
import uuid

from cortex.cbe.encoder import encode
from cortex.cbe.types import CortexValue

# Normative Constant: Cortex System Namespace
NAMESPACE_CORTEX_SYSTEM = uuid.UUID("a1b2c3d4-0000-5000-8000-000000000001")
NAMESPACE_CORTEX_SYSTEM_BYTES = NAMESPACE_CORTEX_SYSTEM.bytes


def compute_raw_uuidv5(namespace_bytes: bytes, name_bytes: bytes) -> tuple[str, str]:
    """
    Computes both raw SHA-1 digest hex and RFC 4122 UUIDv5 directly over byte sequences.
    """
    hasher = hashlib.sha1()
    hasher.update(namespace_bytes)
    hasher.update(name_bytes)
    sha1_hex = hasher.hexdigest()
    full_sha1_bytes = hasher.digest()

    raw_16 = bytearray(full_sha1_bytes[:16])
    raw_16[6] = (raw_16[6] & 0x0F) | 0x50  # Version 5
    raw_16[8] = (raw_16[8] & 0x3F) | 0x80  # Variant RFC 4122

    uuid_str = str(uuid.UUID(bytes=bytes(raw_16)))
    return sha1_hex, uuid_str


def derive_logical_event_id(
    workflow_id: str, command_type: str, causation_id: str, payload: dict
) -> tuple[bytes, str, str, str]:
    """
    Canonical P_semantic 4-Tuple Construction:
    [workflow_id, command_type, causation_id, payload] -> CBE Bytes -> SHA1 -> UUIDv5
    """
    tuple_ast = CortexValue.from_python([workflow_id, command_type, causation_id, payload])
    cbe_bytes = encode(tuple_ast)
    hex_str = cbe_bytes.hex()
    sha1_hex, uuid_str = compute_raw_uuidv5(NAMESPACE_CORTEX_SYSTEM_BYTES, cbe_bytes)
    return cbe_bytes, hex_str, sha1_hex, uuid_str


VECTORS = {
    "TV-A": {
        "workflow_id": "wf-101",
        "command_type": "payment:charge",
        "causation_id": "caus-999",
        "payload": {"amount": 100, "currency": "USD"},
        "expected_cbe": "L4:S6:wf-101S14:payment:chargeS8:caus-999M2:S6:amountI100S8:currencyS3:USD",
        "expected_uuid": "a6afec1e-b59d-55f4-ac38-f6ae6d37d268",
    },
    "TV-B": {
        "workflow_id": "wf-102",
        "command_type": "file:write",
        "causation_id": "caus-1000",
        "payload": {"path": "/tmp/data.txt"},
        "expected_cbe": "L4:S6:wf-102S10:file:writeS9:caus-1000M1:S4:pathS13:/tmp/data.txt",
        "expected_uuid": "d926fda1-f3ea-5672-bd7f-d2858358b002",
    },
    "TV-C": {
        "workflow_id": "wf-103",
        "command_type": "email:send",
        "causation_id": "caus-1001",
        "payload": {"to": "user@example.com"},
        "expected_cbe": "L4:S6:wf-103S10:email:sendS9:caus-1001M1:S2:toS16:user@example.com",
        "expected_uuid": "c588d5ca-4c8b-5f7b-8ebc-0227244f6820",
    },
    "TV-Root": {
        "workflow_id": "wf-777",
        "command_type": "order:process",
        "causation_id": "00000000-0000-0000-0000-000000000000",
        "payload": [],
        "expected_cbe": "L4:S6:wf-777S13:order:processS36:00000000-0000-0000-0000-000000000000L0:",
        "expected_uuid": "983e24da-d481-5a1b-8624-26c18f8b6b01",
    },
}
