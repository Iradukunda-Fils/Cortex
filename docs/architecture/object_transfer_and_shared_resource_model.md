# CORTEX — OBJECTREF & SHARED RESOURCE ARCHITECTURE SPECIFICATION

**Document Identifier:** `CORTEX-SPEC-OBJECT-2026-V1.5`  
**Classification:** Canonical Storage & Data Transport Specification  
**Subsystem:** Content-Addressed Object Architecture & Shared Resource Protection  
**Status:** ARCHITECTURE-LOCKED & FROZEN (v1.5.0-FROZEN)  
**Canonical Schema Namespace:** `https://schemas.cortex.internal/v1`

---

## 1. CANONICAL `ObjectRef` ARCHITECTURE

Large binary payloads (videos, audio, PDFs, datasets, images $> 16\text{ MiB}$) MUST NOT transit the Gateway CBE binary IPC stream directly. Instead, Cortex uses a canonical, content-addressed `ObjectRef` handle abstraction.

### ObjectRef Metadata Schema:
```json
{
  "$schema": "https://schemas.cortex.internal/v1/objectref.json",
  "object_id": "obj_01H8X9A0000000000000000001",
  "version": 1,
  "content_digest": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "size_bytes": 1073741824,
  "media_type": "video/mp4",
  "provenance": {
    "producer_invocation_id": "inv_01J8X8...",
    "state_domain_key": "media_pipeline_v2"
  }
}
```

---

## 2. OPAQUE LOCATOR HANDLES & ZERO-TRUST AUTHORIZATION

`ObjectRef` is purely an identifier and integrity witness, NOT an authorization token. Access requires explicit zero-trust authorization evaluation:

$$\text{Access} = \text{Identity} \land \text{Capability} \land \text{ResourcePolicy} \land \text{InvocationAuthority}$$

Physical storage locators are decoupled from `ObjectRef` and returned as ephemeral, opaque handles (`PhysicalLocatorHandle`):

### Ephemeral PhysicalLocatorHandle Schema:
```json
{
  "$schema": "https://schemas.cortex.internal/v1/physical-locator-handle.json",
  "locator_id": "loc_01H8X9B0000000000000000001",
  "storage_engine_id": "engine_s3_primary",
  "bound_invocation_id": "inv_01J8X9A0000000000000000001",
  "bound_execution_attempt_id": "att_01J8X9A0000000000000000002",
  "access_mode": "READ_ONLY",
  "valid_from_unix_ms": 1756000000000,
  "valid_until_unix_ms": 1756000900000
}
```

---

## 3. STREAMING INTEGRITY VERIFICATION ($O(\text{chunk\_size})$ BOUND)

Object verification uses chunked binary streaming (`ByteStreamReader`), enforcing a hard upper bound of $64\,\text{KiB}$ on memory buffer allocation regardless of overall object size:

$$\text{Memory}_{\text{verification}} = O(\text{chunk\_size}) \quad (\text{chunk\_size} \le 64\,\text{KiB})$$

```rust
pub const MAX_VERIFICATION_CHUNK_SIZE: usize = 65536; // 64 KiB Limit

pub trait ByteStreamReader {
    fn read_chunk(&mut self, buf: &mut [u8]) -> Result<usize, std::io::Error>;
}

pub trait DataPlaneResolver: Send + Sync {
    fn resolve_locator(
        &self, 
        auth_ctx: &AdapterExecutionContext, 
        obj_ref: &ObjectRef
    ) -> Result<PhysicalLocatorHandle, AccessDeniedError>;

    fn verify_integrity_stream(
        &self,
        obj_ref: &ObjectRef,
        stream: &mut dyn ByteStreamReader,
    ) -> Result<bool, IntegrityVerificationError>;
}
```

---

## 4. MULTI-WORKER SHARED RESOURCE SAFETY & WRITE PROTOCOLS

### Immutable Shared Reads (Safe):
Multiple worker replicas can concurrently read the same `ObjectRef` without coordination:
```
Worker Replica A ──┐
Worker Replica B ──┼── READ ──> [ Data Plane ObjectRef (sha256:e3b0c442...) ]
Worker Replica C ──┘
```

### Concurrent Mutable Write Protocol (Fenced):
Direct uncoordinated concurrent writing to a shared target path by multiple workers is strictly forbidden:
```
Worker Replica A ── WRITE ──┐
                            ├──> [ Gateway StateDomainKey Lock ] ──> Atomic Rename/Publish ──> Object Y
Worker Replica B ── WRITE ──┘
```

1. **`StateDomainKey` Fencing:** Acquire exclusive domain lock via Gateway.
2. **Copy-On-Write (COW) Staging:** Write to an isolated temporary file (`/tmp/sandbox_<id>/staging.tmp`).
3. **Atomic Swap & Directory Fsync:** Publication uses atomic rename (`os.replace`) followed by parent directory `fsync`.
4. **Compare-And-Swap (CAS):** Mutative commits publish a new `ObjectRef` version, preserving prior versions as immutable history.
