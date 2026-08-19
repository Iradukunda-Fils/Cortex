"""
Linearizable Gateway Lease Manager (Phase 2)

Enforces atomic, mutually exclusive commit and revocation fencing bound to monotonic
LeaseEpoch counters. Stale commits are rejected with StaleLeaseError.

LINEARIZABILITY DOMAIN: Single Gateway Authority Domain.
Future multi-process or multi-node Gateway implementations MUST preserve
linearizable mutually exclusive commit and revocation fencing at this boundary.
"""

import threading
import uuid
from dataclasses import dataclass
from typing import Dict

from cortex.tools.kernel.replica.identity import OwnershipIdentity


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
