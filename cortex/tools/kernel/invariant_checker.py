"""
Issue #49 (Phase 6.0): Runtime Enforcement of the 10 Core Kernel Obligations
Normative Architecture Baseline: v1.5.1-FINAL-FROZEN
Specification: Section 2 (Assurance Class Mapping for the 10 Core Kernel Obligations)

10 Core Kernel Obligations:
Proof 1: Assignment Uniqueness (forall I: |{a in A : a.invocation = I}| <= 1)
Proof 2: Worker Capacity Bounds (forall w in W: 0 <= active_load <= max_concurrency)
Proof 3: Capacity Conservation (sum_w active_load == |A_ACTIVE|)
Proof 4: Lease Fencing Safety (e_L != E_L_active(I) => REJECT)
Proof 5: Worker Incarnation Fencing (g != g_active(w) => REJECT)
Proof 6: Authority Epoch Fenced (e_A != E_A_active => REJECT)
Proof 7: Quarantine Containment (I in Q => UnsafeRetry(I) = REJECT)
Proof 8: WAL Deterministic Replay (D_1 == D_2 => Replay(D_1) == Replay(D_2))
Proof 9: Universal Resource Bounds (forall X: Count(X) <= B_X and ByteSize(X) <= S_X)
Proof 10: Recovery Invariant Preservation (ValidPrefix(D) => Invariant(Replay(D)))
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Mapping, Set

from cortex.tools.kernel.resource_bounds import ResourceBoundValidator

logger = logging.getLogger(__name__)


class KernelInvariantViolationError(Exception):
    """Raised when any of the 10 Core Kernel Obligations is violated at runtime."""

    def __init__(self, proof_id: str, description: str) -> None:
        super().__init__(f"Kernel Invariant Violation [{proof_id}]: {description}")
        self.proof_id = proof_id
        self.description = description


class KernelInvariantChecker:
    """
    Executable Runtime Invariant Checker for the 10 Core Kernel Obligations.
    Target Assurance Class: RUNTIME-ENFORCED
    """

    @staticmethod
    def verify_proof_1_assignment_uniqueness(active_assignments: Mapping[str, Any]) -> None:
        """
        Proof 1: Assignment Uniqueness.
        Ensures an invocation I has at most one active execution assignment.
        """
        seen_invocations: Set[str] = set()
        for inv_id in active_assignments.keys():
            if inv_id in seen_invocations:
                raise KernelInvariantViolationError(
                    "Proof 1 (Assignment Uniqueness)",
                    f"Duplicate active assignment detected for invocation '{inv_id}'",
                )
            seen_invocations.add(inv_id)

    @staticmethod
    def verify_proof_2_worker_capacity_bounds(workers: Mapping[str, Any]) -> None:
        """
        Proof 2: Worker Capacity Bounds.
        Ensures 0 <= active_load <= max_concurrency for all registered workers.
        """
        for worker_id, worker in workers.items():
            active = getattr(worker, "active_load", 0)
            max_c = getattr(worker, "max_concurrency", 0)
            if active < 0:
                raise KernelInvariantViolationError(
                    "Proof 2 (Worker Capacity Bounds)",
                    f"Worker '{worker_id}' has negative active_load {active}",
                )
            if active > max_c:
                raise KernelInvariantViolationError(
                    "Proof 2 (Worker Capacity Bounds)",
                    f"Worker '{worker_id}' active_load {active} exceeds max_concurrency {max_c}",
                )

    @staticmethod
    def verify_proof_3_capacity_conservation(workers: Mapping[str, Any], active_assignments: Mapping[str, Any]) -> None:
        """
        Proof 3: Capacity Conservation Law.
        Ensures sum_{w in W} active_load(w) == |A_ACTIVE|.
        """
        total_worker_load = sum(getattr(w, "active_load", 0) for w in workers.values())
        active_assignment_count = len(active_assignments)
        if total_worker_load != active_assignment_count:
            raise KernelInvariantViolationError(
                "Proof 3 (Capacity Conservation)",
                f"Sum of active loads ({total_worker_load}) != active assignment count ({active_assignment_count})",
            )

    @staticmethod
    def verify_proof_4_lease_fencing(requested_lease_epoch: int, active_lease_epoch: int, invocation_id: str) -> None:
        """
        Proof 4: Lease Fencing Safety.
        Rejects commits or operations where requested lease_epoch != active_lease_epoch.
        """
        if requested_lease_epoch != active_lease_epoch:
            raise KernelInvariantViolationError(
                "Proof 4 (Lease Fencing Safety)",
                f"Invocation '{invocation_id}' requested lease epoch {requested_lease_epoch} != active {active_lease_epoch}",
            )

    @staticmethod
    def verify_proof_5_incarnation_fencing(presented_generation: int, active_generation: int, worker_id: str) -> None:
        """
        Proof 5: Worker Incarnation Fencing.
        Rejects operations from stale process generations (presented_generation != active_generation).
        """
        if presented_generation != active_generation:
            raise KernelInvariantViolationError(
                "Proof 5 (Worker Incarnation Fencing)",
                f"Worker '{worker_id}' presented generation {presented_generation} != active {active_generation}",
            )

    @staticmethod
    def verify_proof_6_authority_epoch_fencing(presented_authority_epoch: int, active_authority_epoch: int) -> None:
        """
        Proof 6: Authority Epoch Fenced.
        Rejects commits presented under stale cluster authority epoch (presented_authority_epoch != active_authority_epoch).
        """
        if presented_authority_epoch != active_authority_epoch:
            raise KernelInvariantViolationError(
                "Proof 6 (Authority Epoch Fencing)",
                f"Presented authority epoch {presented_authority_epoch} != active {active_authority_epoch}",
            )

    @staticmethod
    def verify_proof_7_quarantine_containment(quarantined_store: Mapping[str, Any], invocation_id: str) -> None:
        """
        Proof 7: Quarantine Containment.
        Ensures unsafe retries on quarantined invocations are strictly rejected.
        """
        if invocation_id in quarantined_store:
            raise KernelInvariantViolationError(
                "Proof 7 (Quarantine Containment)",
                f"Invocation '{invocation_id}' is isolated in quarantine; un-reconciled retry rejected",
            )

    @staticmethod
    def verify_proof_8_wal_replay_determinism(replay_fn: Callable[[bytes], Any], wal_bytes_1: bytes, wal_bytes_2: bytes) -> None:
        """
        Proof 8: WAL Deterministic Replay.
        Verifies D_1 == D_2 => Replay(D_1) == Replay(D_2).
        """
        if wal_bytes_1 != wal_bytes_2:
            raise ValueError("WAL byte streams must be identical to verify determinism.")
        state1 = replay_fn(wal_bytes_1)
        state2 = replay_fn(wal_bytes_2)
        if state1 != state2:
            raise KernelInvariantViolationError(
                "Proof 8 (WAL Deterministic Replay)",
                "Identical WAL byte inputs produced non-deterministic replay state outputs",
            )

    @staticmethod
    def verify_proof_9_universal_resource_bounds(
        validator: ResourceBoundValidator,
        resource_counts: Mapping[str, int],
        resource_bytes: Mapping[str, int],
    ) -> None:
        """
        Proof 9: Universal Resource Bounds.
        Ensures Count(X) <= B_X and ByteSize(X) <= S_X across all system state containers.
        """
        for r_name, count in resource_counts.items():
            b_size = resource_bytes.get(r_name, 0)
            violated, action, reason = validator.evaluate(r_name, count, b_size)
            if violated:
                action_str = action.value if action is not None else "UNKNOWN"
                raise KernelInvariantViolationError(
                    "Proof 9 (Universal Resource Bounds)",
                    f"Resource container '{r_name}' violated bounds: {reason}. Action: {action_str}",
                )

    @staticmethod
    def verify_proof_10_recovery_invariant_preservation(
        replay_fn: Callable[[bytes], Any],
        state_invariant_fn: Callable[[Any], bool],
        wal_prefix_bytes: bytes,
    ) -> None:
        """
        Proof 10: Recovery Invariant Preservation.
        Verifies ValidPrefix(D) => Invariant(Replay(D)).
        """
        recovered_state = replay_fn(wal_prefix_bytes)
        if not state_invariant_fn(recovered_state):
            raise KernelInvariantViolationError(
                "Proof 10 (Recovery Invariant Preservation)",
                "Replayed WAL prefix produced a state violating system safety invariants",
            )

    @staticmethod
    def verify_derived_capability_index_consistency(
        workers: Mapping[str, Any],
        capability_index: Mapping[str, Set[str]],
    ) -> None:
        """
        Invariant I_9: Derived Capability Index Consistency.
        Formula: w in Index[c] <==> w in W and c in Capabilities(w).
        Ensures derived read view Index = f(S_A) is 100% synchronized with authoritative state S_A.
        """
        # Forward check: Index[c] contains only valid registered workers with capability c
        for cap, worker_ids in capability_index.items():
            for wid in worker_ids:
                if wid not in workers:
                    raise KernelInvariantViolationError(
                        "Invariant I_9 (Derived Capability Index Consistency)",
                        f"Stale worker '{wid}' present in derived index for capability '{cap}'",
                    )
                w_caps = getattr(workers[wid], "capabilities", set())
                if cap not in w_caps:
                    raise KernelInvariantViolationError(
                        "Invariant I_9 (Derived Capability Index Consistency)",
                        f"Worker '{wid}' in index[{cap}] lacks capability '{cap}'",
                    )
        # Reverse check: Every registered worker capability is indexed
        for wid, worker in workers.items():
            w_caps = getattr(worker, "capabilities", set())
            for cap in w_caps:
                if cap not in capability_index or wid not in capability_index[cap]:
                    raise KernelInvariantViolationError(
                        "Invariant I_9 (Derived Capability Index Consistency)",
                        f"Registered worker '{wid}' with capability '{cap}' missing from derived index",
                    )

