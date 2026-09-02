"""
Cortex Distributed & Restart Gateway Reconciliation Engine — Sub-Gate B.3

Coordinates Dual-Epoch Fencing, Cross-Gateway Mutex Claim, WAL Transitions,
and Deterministic Crash Recovery.

Key Safety Invariants:
    1. ActiveExternalExecutions(key) <= 1 across all Gateway processes.
    2. Persist(ADMITTED) -> fsync -> Persist(ACTUATING) -> fsync -> External Dispatch.
    3. AuthorityEpoch mismatch or LeaseEpoch mismatch -> StaleEpochError (reject execution).
    4. Crash during ACTUATING -> Recover -> UNKNOWN -> QUARANTINED (no blind retries).
    5. Replay of COMMITTED key returns exact original EffectOutcome (including evidence).
"""

from __future__ import annotations

import fcntl
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from cortex.tools.kernel.adapter_contract import (
    AdapterExecutionContext,
    ExecutionStatus,
    ResourceContract,
)
from cortex.tools.kernel.effect_gateway import EffectOutcome
from cortex.tools.kernel.effect_wal import (
    EffectWALEngine,
    EffectWALRecord,
    EffectWALState,
)

logger = logging.getLogger(__name__)


class StaleEpochError(Exception):
    """Raised when request lease epoch or authority epoch fails active fence check."""


class EffectInFlightError(Exception):
    """Raised when another Gateway process holds an active execution claim for EffectKey."""


class CrossGatewayClaimLock:
    """
    Cross-process atomic claim lock for EffectKeys across Gateway replicas.
    Uses OS file locks (fcntl.flock) on shared claim lockfiles.
    """

    def __init__(self, lock_dir: str = "/tmp/cortex_effect_claims") -> None:
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)

    def acquire_claim(self, effect_key: str) -> Optional[Any]:
        """
        Attempts non-blocking cross-process lock acquisition.
        Uses SHA-256 hash of effect_key for safe, traversal-free path derivation.
        Returns open file handle if acquired, or None if lock held by another Gateway process.
        """
        safe_hash = hashlib.sha256(effect_key.encode("utf-8")).hexdigest()
        lock_file = self.lock_dir / f"{safe_hash}.lock"
        try:
            f = open(lock_file, "w")
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return f
        except (IOError, OSError):
            return None


    def release_claim(self, lock_handle: Optional[Any]) -> None:
        if lock_handle is not None and not lock_handle.closed:
            try:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
                lock_handle.close()
            except (IOError, OSError):
                pass


class GatewayReconciliationEngine:
    """
    Coordinates Fenced Execution, WAL Transitions, and Restart Recovery across Gateways.
    """

    def __init__(
        self,
        wal_engine: EffectWALEngine,
        active_lease_epoch: int,
        active_authority_epoch: int,
        lock_dir: str = "/tmp/cortex_effect_claims",
    ) -> None:
        self._wal = wal_engine
        self._lease_epoch = active_lease_epoch
        self._authority_epoch = active_authority_epoch
        self._claim_mutex = CrossGatewayClaimLock(lock_dir=lock_dir)

        # Authoritative state reconstructed from persistent WAL
        self._record_cache: Dict[str, EffectWALRecord] = {}

        # Run deterministic recovery on startup
        self.recover_from_wal()

    def recover_from_wal(self) -> None:
        """
        Reconstructs state matrix from WAL records.
        Converts unresolved ACTUATING records to QUARANTINED.
        """
        records = self._wal.replay_all_records()
        latest_by_key: Dict[str, EffectWALRecord] = {}

        for rec in records:
            latest_by_key[rec.effect_key] = rec

        for key, rec in latest_by_key.items():
            if rec.state == EffectWALState.ACTUATING:
                # Crash during external execution -> Force QUARANTINED
                quarantined_rec = self._wal.append_record(
                    invocation_id=rec.invocation_id,
                    effect_key=rec.effect_key,
                    lease_epoch=rec.lease_epoch,
                    authority_epoch=self._authority_epoch,
                    state=EffectWALState.QUARANTINED,
                    payload=rec.payload,
                    error_message=(
                        "Gateway crash recovery: Unresolved ACTUATING effect "
                        "transitioned to QUARANTINED. Manual reconciliation required."
                    ),
                )
                self._record_cache[key] = quarantined_rec
            else:
                self._record_cache[key] = rec

    def execute_fenced_effect(
        self,
        invocation_id: str,
        execution_attempt_id: str,
        effect_key: str,
        lease_epoch: int,
        authority_epoch: int,
        payload: bytes,
        adapter: ResourceContract,
        resource_id: str = "mcp_resource",
        operation_type: str = "execute",
    ) -> EffectOutcome:
        """
        Executes an effect with dual-epoch fencing, cross-gateway locking, and WAL persistence.
        """
        # Step 1: Strict Dual Epoch Fencing Check
        if lease_epoch != self._lease_epoch:
            raise StaleEpochError(
                f"Lease epoch mismatch: request={lease_epoch} != active={self._lease_epoch}"
            )
        if authority_epoch != self._authority_epoch:
            raise StaleEpochError(
                f"Authority epoch mismatch: request={authority_epoch} != active={self._authority_epoch}"
            )

        # Step 2: Check for existing committed or quarantined state
        if effect_key in self._record_cache:
            existing = self._record_cache[effect_key]
            if existing.state == EffectWALState.COMMITTED and existing.outcome is not None:
                logger.info("Replay hit for COMMITTED effect key=%s", effect_key[:24])
                return existing.outcome
            elif existing.state == EffectWALState.QUARANTINED:
                return EffectOutcome(
                    invocation_id=invocation_id,
                    execution_attempt_id=execution_attempt_id,
                    status=ExecutionStatus.UNKNOWN_EFFECT,
                    error_message=(
                        "Replay denied: Effect is in QUARANTINED state due to a previous "
                        "Gateway crash or indeterminate state. Blind retry blocked."
                    ),
                )

        # Step 3: Cross-Gateway Atomic Claim Mutex
        lock_handle = self._claim_mutex.acquire_claim(effect_key)
        if lock_handle is None:
            raise EffectInFlightError(
                f"Active external execution already in progress across Gateways for key: {effect_key}"
            )

        try:
            # Step 4: Persist ADMITTED state -> fsync
            self._wal.append_record(
                invocation_id=invocation_id,
                effect_key=effect_key,
                lease_epoch=lease_epoch,
                authority_epoch=authority_epoch,
                state=EffectWALState.ADMITTED,
                payload=payload,
            )

            # Step 5: Persist ACTUATING state -> fsync
            self._wal.append_record(
                invocation_id=invocation_id,
                effect_key=effect_key,
                lease_epoch=lease_epoch,
                authority_epoch=authority_epoch,
                state=EffectWALState.ACTUATING,
                payload=payload,
            )

            # Step 6: Dispatch External Adapter Execution
            ctx = AdapterExecutionContext(
                invocation_id=invocation_id,
                execution_attempt_id=execution_attempt_id,
                adapter_request_id=f"req_{effect_key[:12]}",
                idempotency_key=effect_key,
                lease_epoch=lease_epoch,
                resource_id=resource_id,
                operation_type=operation_type,
            )
            from cortex.tools.kernel.adapter_contract import EffectPayload
            adapter_outcome = adapter.execute_effect(ctx, EffectPayload(data=payload))

            # Step 7: Build EffectOutcome & Persist COMMITTED state -> fsync
            effect_outcome = EffectOutcome(
                invocation_id=invocation_id,
                execution_attempt_id=execution_attempt_id,
                status=adapter_outcome.status,
                evidence=adapter_outcome.evidence,
                error_message=adapter_outcome.error_message,
            )

            final_state = (
                EffectWALState.COMMITTED
                if adapter_outcome.status == ExecutionStatus.EFFECT_CONFIRMED
                else EffectWALState.QUARANTINED
            )

            committed_rec = self._wal.append_record(
                invocation_id=invocation_id,
                effect_key=effect_key,
                lease_epoch=lease_epoch,
                authority_epoch=authority_epoch,
                state=final_state,
                payload=payload,
                outcome=effect_outcome,
                error_message=adapter_outcome.error_message,
            )

            self._record_cache[effect_key] = committed_rec
            return effect_outcome

        finally:
            self._claim_mutex.release_claim(lock_handle)

