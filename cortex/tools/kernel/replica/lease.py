"""
Linearizable Gateway Lease Manager (Phase 2 & 4)

Enforces atomic, mutually exclusive commit and revocation fencing bound to monotonic
LeaseEpoch counters. Stale commits are rejected with StaleLeaseError.

LINEARIZABILITY DOMAIN: Single Gateway Authority Domain.
Future multi-process or multi-node Gateway implementations MUST preserve
linearizable mutually exclusive commit and revocation fencing at this boundary.
"""

import threading
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict

from cortex.tools.kernel.replica.identity import OwnershipIdentity
from cortex.tools.kernel.replica.lifecycle import WorkerLifecycleStage

if TYPE_CHECKING:
    from cortex.tools.kernel.replica.router import WorkerRef


class StaleLeaseError(Exception):
    """Raised when a commit attempt uses a revoked or stale lease epoch (ERR_STALE_LEASE_EPOCH)."""

    pass


@dataclass
class LeaseRecord:
    ownership_identity: OwnershipIdentity
    assigned_worker_id: str
    active: bool = True
    committed: bool = False


class LeaseManager:
    """Thread-safe, linearizable Gateway Lease Authority (Single Gateway Authority Domain)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # invocation_id -> LeaseRecord
        self._active_leases: Dict[str, LeaseRecord] = {}
        # invocation_id -> current_epoch
        self._latest_epoch: Dict[str, int] = {}
        # worker_id -> WorkerRef (active registered Gateway worker state)
        self._worker_registry: Dict[str, "WorkerRef"] = {}

    def register_worker_state(self, worker_ref: "WorkerRef") -> None:
        """Register or update active worker replica state in the Gateway TCB registry."""
        with self._lock:
            self._worker_registry[worker_ref.instance_id] = worker_ref

    def unregister_worker(self, worker_id: str) -> None:
        """Remove worker replica from Gateway TCB registry on eviction or process death."""
        with self._lock:
            self._worker_registry.pop(worker_id, None)

    def revalidate_candidate(
        self,
        worker_ref: "WorkerRef",
        active_config_gen: int,
        active_config_hash: str,
        active_sandbox_hash: str,
        active_cap_hash: str,
        max_inflight: int = 10,
    ) -> bool:
        """Atomically revalidate a proposed candidate snapshot inside the Gateway TCB lock.

        Checks:
        1. Worker exists in active registry
        2. lifecycle_version matches registry version
        3. stage == READY
        4. config_generation matches active_config_gen
        5. config_hash matches active_config_hash
        6. sandbox_profile_hash matches active_sandbox_hash
        7. capability_envelope_hash matches active_cap_hash
        8. active inflight leases < max_inflight
        """
        with self._lock:
            registered = self._worker_registry.get(worker_ref.instance_id)
            if not registered:
                return False

            if registered.lifecycle_version != worker_ref.lifecycle_version:
                return False

            if registered.stage != WorkerLifecycleStage.READY:
                return False

            if registered.config_generation != active_config_gen:
                return False

            if registered.config_hash != active_config_hash:
                return False

            if registered.sandbox_profile_hash != active_sandbox_hash:
                return False

            if registered.capability_envelope_hash != active_cap_hash:
                return False

            # Calculate active inflight leases for this worker
            active_count = sum(
                1 for rec in self._active_leases.values()
                if rec.assigned_worker_id == worker_ref.instance_id and rec.active and not rec.committed
            )
            if active_count >= max_inflight:
                return False

            return True

    def grant_lease(self, invocation_id: str, worker_id: str) -> OwnershipIdentity:
        """Atomically grants an epoch-bound lease to a worker for an invocation."""
        with self._lock:
            current_epoch = self._latest_epoch.get(invocation_id, 0) + 1
            self._latest_epoch[invocation_id] = current_epoch

            lease_id = str(uuid.uuid4())
            ownership = OwnershipIdentity(
                invocation_id=invocation_id,
                lease_id=lease_id,
                lease_epoch=current_epoch,
            )

            record = LeaseRecord(
                ownership_identity=ownership,
                assigned_worker_id=worker_id,
                active=True,
                committed=False,
            )
            self._active_leases[invocation_id] = record
            return ownership

    def commit_invocation(self, invocation_id: str, lease_epoch: int) -> bool:
        """Atomically commits an invocation under a specific lease epoch.

        Must be mutually exclusive with revoke_lease. If lease_epoch != active lease epoch,
        or lease is inactive, raises StaleLeaseError.
        """
        with self._lock:
            record = self._active_leases.get(invocation_id)
            if not record:
                raise StaleLeaseError(f"ERR_STALE_LEASE_EPOCH: No active lease found for {invocation_id}")

            if not record.active:
                raise StaleLeaseError(f"ERR_STALE_LEASE_EPOCH: Lease for {invocation_id} has been revoked")

            if record.ownership_identity.lease_epoch != lease_epoch:
                raise StaleLeaseError(
                    f"ERR_STALE_LEASE_EPOCH: Commit epoch {lease_epoch} does not match active epoch {record.ownership_identity.lease_epoch}"
                )

            record.committed = True
            record.active = False
            return True

    def revoke_lease(self, invocation_id: str, lease_epoch: int) -> bool:
        """Atomically revokes a lease for an invocation under a specific lease epoch.

        Must be mutually exclusive with commit_invocation. Returns True if lease was revoked.
        """
        with self._lock:
            record = self._active_leases.get(invocation_id)
            if not record:
                return False

            if record.ownership_identity.lease_epoch == lease_epoch and record.active:
                record.active = False
                return True
            return False

    def is_lease_valid(self, invocation_id: str, lease_epoch: int) -> bool:
        """Returns True iff the lease is active and matches lease_epoch."""
        with self._lock:
            record = self._active_leases.get(invocation_id)
            if not record:
                return False
            return record.active and record.ownership_identity.lease_epoch == lease_epoch
