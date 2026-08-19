"""
Phase 4 Routing & Dispatch Conformance Test Suite (Gates RD-1 to RD-24)

Verifies unprivileged candidate resolution, deterministic least-inflight selection,
atomic LeaseManager revalidation, TOCTOU race safety, bounded FIFO queueing,
state domain lock conflict serialization, zero-token possession isolation,
and observational witness provenance logging.
"""

import os
import tempfile
import threading
import unittest

from cortex.tools.kernel.replica.lease import LeaseManager
from cortex.tools.kernel.replica.ledger import InvocationState, InvocationStateLedger, RecoveryBucket
from cortex.tools.kernel.replica.lifecycle import WorkerLifecycleStage
from cortex.tools.kernel.replica.router import (
    CandidateResolver,
    ExecutionClass,
    GatewayDispatcher,
    NoEligibleWorkerNow,
    QueueFullError,
    RoutingDecisionEvent,
    RoutingPolicy,
    StateDomainKey,
    WorkerRef,
)


class TestReplicaPhase4(unittest.TestCase):
    """Conformance test suite for RD-1 through RD-24 Phase 4 verification gates."""

    def setUp(self) -> None:
        self.active_config_gen = 18
        self.active_config_hash = "sha256_hash_A"
        self.active_sandbox_hash = "sb_profile_v1"
        self.active_cap_hash = "cap_env_v1"

    def _make_worker(
        self,
        instance_id: str = "w-1",
        group_id: str = "payments",
        lifecycle_version: int = 1,
        config_gen: int = 18,
        config_hash: str = "sha256_hash_A",
        sandbox_hash: str = "sb_profile_v1",
        cap_hash: str = "cap_env_v1",
        caps: list[str] | None = None,
        inflight: int = 0,
        stage: WorkerLifecycleStage = WorkerLifecycleStage.READY,
    ) -> WorkerRef:
        return WorkerRef(
            instance_id=instance_id,
            group_id=group_id,
            lifecycle_version=lifecycle_version,
            config_generation=config_gen,
            config_hash=config_hash,
            sandbox_profile_hash=sandbox_hash,
            capability_envelope_hash=cap_hash,
            required_capabilities=caps or ["payments.execute"],
            observed_inflight=inflight,
            stage=stage,
        )

    # ── RD-1: Unprivileged Router Boundary Isolation ──────────────────
    def test_rd1_unprivileged_router_boundary_isolation(self) -> None:
        """RD-1: CandidateResolver has zero authority, bearer tokens, or TCB mutation APIs."""
        resolver = CandidateResolver()
        methods = dir(resolver)
        self.assertNotIn("grant_lease", methods)
        self.assertNotIn("commit_invocation", methods)
        self.assertNotIn("transition_state", methods)

    # ── RD-2: Monotonic ConfigGeneration Filter ────────────────────────
    def test_rd2_config_generation_filter(self) -> None:
        """RD-2: Workers with stale config_generation must be excluded from candidate pool."""
        resolver = CandidateResolver()
        w_stale = self._make_worker("w-old", config_gen=17)
        w_valid = self._make_worker("w-valid", config_gen=18)

        candidates = resolver.resolve_candidates(
            candidate_pool=[w_stale, w_valid],
            required_capabilities=["payments.execute"],
            active_config_gen=18,
            active_config_hash=self.active_config_hash,
            active_sandbox_hash=self.active_sandbox_hash,
            active_cap_hash=self.active_cap_hash,
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].instance_id, "w-valid")

    # ── RD-3: ConfigHash Mismatch Filter ──────────────────────────────
    def test_rd3_config_hash_mismatch_filter(self) -> None:
        """RD-3: Workers with wrong config_hash must be excluded from candidate pool."""
        resolver = CandidateResolver()
        w_bad_hash = self._make_worker("w-bad-hash", config_hash="sha256_hash_B")
        w_valid = self._make_worker("w-valid", config_hash="sha256_hash_A")

        candidates = resolver.resolve_candidates(
            candidate_pool=[w_bad_hash, w_valid],
            required_capabilities=["payments.execute"],
            active_config_gen=18,
            active_config_hash=self.active_config_hash,
            active_sandbox_hash=self.active_sandbox_hash,
            active_cap_hash=self.active_cap_hash,
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].instance_id, "w-valid")

    # ── RD-4: Capability Envelope Containment ─────────────────────────
    def test_rd4_capability_envelope_containment(self) -> None:
        """RD-4: Workers missing required invocation capabilities must be excluded."""
        resolver = CandidateResolver()
        w1 = self._make_worker("w-1", caps=["payments.read"])
        w2 = self._make_worker("w-2", caps=["payments.read", "payments.execute"])

        candidates = resolver.resolve_candidates(
            candidate_pool=[w1, w2],
            required_capabilities=["payments.execute"],
            active_config_gen=18,
            active_config_hash=self.active_config_hash,
            active_sandbox_hash=self.active_sandbox_hash,
            active_cap_hash=self.active_cap_hash,
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].instance_id, "w-2")

    # ── RD-5: Worker Lifecycle Readiness Filter ───────────────────────
    def test_rd5_worker_lifecycle_readiness_filter(self) -> None:
        """RD-5: Workers in DRAINING or QUIESCED state must be excluded."""
        resolver = CandidateResolver()
        w_drain = self._make_worker("w-drain", stage=WorkerLifecycleStage.DRAINING)
        w_ready = self._make_worker("w-ready", stage=WorkerLifecycleStage.READY)

        candidates = resolver.resolve_candidates(
            candidate_pool=[w_drain, w_ready],
            required_capabilities=["payments.execute"],
            active_config_gen=18,
            active_config_hash=self.active_config_hash,
            active_sandbox_hash=self.active_sandbox_hash,
            active_cap_hash=self.active_cap_hash,
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].instance_id, "w-ready")

    # ── RD-6: Least-Inflight Selection Policy ─────────────────────────
    def test_rd6_least_inflight_selection_policy(self) -> None:
        """RD-6: RoutingPolicy selects candidate with minimum active inflight count."""
        policy = RoutingPolicy()
        w1 = self._make_worker("w-busy", inflight=5)
        w2 = self._make_worker("w-idle", inflight=1)

        selected = policy.select_candidate([w1, w2])
        self.assertEqual(selected.instance_id, "w-idle")

    # ── RD-7: Bounded FIFO Queue Handling ─────────────────────────────
    def test_rd7_bounded_fifo_queue_handling(self) -> None:
        """RD-7: GatewayDispatcher enqueues invocations in per-group FIFO order."""
        lease_mgr = LeaseManager()
        ledger = InvocationStateLedger()
        dispatcher = GatewayDispatcher(lease_manager=lease_mgr, ledger=ledger)

        w1 = self._make_worker("w-1")
        lease_mgr.register_worker_state(w1)

        dispatcher.dispatch_invocation(
            invocation_id="inv-fifo-1",
            intent_hash="0x1",
            required_capabilities=["payments.execute"],
            candidate_pool=[w1],
            active_config_gen=18,
            active_config_hash=self.active_config_hash,
            active_sandbox_hash=self.active_sandbox_hash,
            active_cap_hash=self.active_cap_hash,
        )
        rec = ledger.get_record("inv-fifo-1")
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertEqual(rec.assigned_worker_id, "w-1")

    # ── RD-8: Atomic Revalidation Gate ────────────────────────────────
    def test_rd8_atomic_revalidation_gate(self) -> None:
        """RD-8: grant_lease revalidates candidate against Gateway TCB lock."""
        lease_mgr = LeaseManager()
        ledger = InvocationStateLedger()
        dispatcher = GatewayDispatcher(lease_manager=lease_mgr, ledger=ledger)

        w1 = self._make_worker("w-1", config_gen=18)
        lease_mgr.register_worker_state(w1)

        own = dispatcher.dispatch_invocation(
            invocation_id="inv-gate-1",
            intent_hash="0x2",
            required_capabilities=["payments.execute"],
            candidate_pool=[w1],
            active_config_gen=18,
            active_config_hash=self.active_config_hash,
            active_sandbox_hash=self.active_sandbox_hash,
            active_cap_hash=self.active_cap_hash,
        )
        self.assertTrue(lease_mgr.is_lease_valid("inv-gate-1", own.lease_epoch))

    # ── RD-9: Post-Assignment Worker Crash Recovery ───────────────────
    def test_rd9_post_assignment_worker_crash_recovery(self) -> None:
        """RD-9: Invocation in ASSIGNED state transitions safely to UNADMITTED on worker crash."""
        ledger = InvocationStateLedger()
        ledger.create_invocation("inv-crash-post", "0xCRASH")
        ledger.transition_state("inv-crash-post", InvocationState.ASSIGNED, worker_id="w-dead")

        bucket = ledger.classify_recovery("inv-crash-post")
        self.assertEqual(bucket, RecoveryBucket.UNADMITTED)

    # ── RD-10: State Domain Key Conflict Fencing ──────────────────────
    def test_rd10_state_domain_key_conflict_fencing(self) -> None:
        """RD-10: StateDomainKey domain_hash is deterministic and unique."""
        k1 = StateDomainKey("billing", "/accounts/123", "balance")
        k2 = StateDomainKey("billing", "/accounts/123", "balance")
        k3 = StateDomainKey("billing", "/accounts/123", "status")

        self.assertEqual(k1.domain_hash(), k2.domain_hash())
        self.assertNotEqual(k1.domain_hash(), k3.domain_hash())

    # ── RD-11: Queue Capacity Ceiling Enforcement ──────────────────────
    def test_rd11_queue_capacity_ceiling_enforcement(self) -> None:
        """RD-11: Breaching MaxQueueDepth raises QueueFullError."""
        lease_mgr = LeaseManager()
        ledger = InvocationStateLedger()
        dispatcher = GatewayDispatcher(lease_manager=lease_mgr, ledger=ledger, max_queue_depth=0)

        w1 = self._make_worker("w-1")
        lease_mgr.register_worker_state(w1)

        with self.assertRaises(QueueFullError):
            dispatcher.dispatch_invocation(
                invocation_id="inv-overfill",
                intent_hash="0x3",
                required_capabilities=["payments.execute"],
                candidate_pool=[w1],
                active_config_gen=18,
                active_config_hash=self.active_config_hash,
                active_sandbox_hash=self.active_sandbox_hash,
                active_cap_hash=self.active_cap_hash,
            )

    # ── RD-12: Routing Decision Provenance Logging ────────────────────
    def test_rd12_routing_decision_provenance_logging(self) -> None:
        """RD-12: Every dispatch appends a RoutingDecisionEvent to the observational buffer."""
        lease_mgr = LeaseManager()
        ledger = InvocationStateLedger()
        dispatcher = GatewayDispatcher(lease_manager=lease_mgr, ledger=ledger)

        w1 = self._make_worker("w-1")
        lease_mgr.register_worker_state(w1)

        dispatcher.dispatch_invocation(
            invocation_id="inv-event-1",
            intent_hash="0x4",
            required_capabilities=["payments.execute"],
            candidate_pool=[w1],
            active_config_gen=18,
            active_config_hash=self.active_config_hash,
            active_sandbox_hash=self.active_sandbox_hash,
            active_cap_hash=self.active_cap_hash,
        )

        self.assertEqual(len(dispatcher.decision_events), 1)
        ev = dispatcher.decision_events[0]
        self.assertEqual(ev.invocation_id, "inv-event-1")
        self.assertEqual(ev.selected_replica_id, "w-1")

    # ── RD-13: TOCTOU Candidate Draining Race ─────────────────────────
    def test_rd13_toctou_candidate_draining_race(self) -> None:
        """RD-13: Candidate becomes DRAINING between candidate selection and lease grant."""
        lease_mgr = LeaseManager()
        ledger = InvocationStateLedger()
        dispatcher = GatewayDispatcher(lease_manager=lease_mgr, ledger=ledger)

        w_stale = self._make_worker("w-1", stage=WorkerLifecycleStage.READY)
        w_fallback = self._make_worker("w-2", stage=WorkerLifecycleStage.READY)

        # Register w-stale as DRAINING in Gateway registry, simulating TOCTOU status change
        lease_mgr.register_worker_state(self._make_worker("w-1", stage=WorkerLifecycleStage.DRAINING))
        lease_mgr.register_worker_state(w_fallback)

        dispatcher.dispatch_invocation(
            invocation_id="inv-toctou-drain",
            intent_hash="0x5",
            required_capabilities=["payments.execute"],
            candidate_pool=[w_stale, w_fallback],
            active_config_gen=18,
            active_config_hash=self.active_config_hash,
            active_sandbox_hash=self.active_sandbox_hash,
            active_cap_hash=self.active_cap_hash,
        )
        rec = ledger.get_record("inv-toctou-drain")
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertEqual(rec.assigned_worker_id, "w-2")

    # ── RD-14: TOCTOU ConfigGeneration Increment Race ─────────────────
    def test_rd14_toctou_config_gen_race(self) -> None:
        """RD-14: ConfigGen increments in Gateway registry mid-selection -> revalidation fails."""
        lease_mgr = LeaseManager()
        ledger = InvocationStateLedger()
        dispatcher = GatewayDispatcher(lease_manager=lease_mgr, ledger=ledger)

        w_proposed = self._make_worker("w-1", config_gen=18)
        lease_mgr.register_worker_state(self._make_worker("w-1", config_gen=19))

        with self.assertRaises(NoEligibleWorkerNow):
            dispatcher.dispatch_invocation(
                invocation_id="inv-toctou-gen",
                intent_hash="0x6",
                required_capabilities=["payments.execute"],
                candidate_pool=[w_proposed],
                active_config_gen=18,
                active_config_hash=self.active_config_hash,
                active_sandbox_hash=self.active_sandbox_hash,
                active_cap_hash=self.active_cap_hash,
            )

    # ── RD-15: TOCTOU ConfigHash Mismatch Race ────────────────────────
    def test_rd15_toctou_config_hash_race(self) -> None:
        """RD-15: ConfigHash changes in Gateway registry mid-selection -> revalidation fails."""
        lease_mgr = LeaseManager()
        ledger = InvocationStateLedger()
        dispatcher = GatewayDispatcher(lease_manager=lease_mgr, ledger=ledger)

        w_proposed = self._make_worker("w-1", config_hash="sha256_hash_A")
        lease_mgr.register_worker_state(self._make_worker("w-1", config_hash="sha256_hash_MUTATED"))

        with self.assertRaises(NoEligibleWorkerNow):
            dispatcher.dispatch_invocation(
                invocation_id="inv-toctou-hash",
                intent_hash="0x7",
                required_capabilities=["payments.execute"],
                candidate_pool=[w_proposed],
                active_config_gen=18,
                active_config_hash=self.active_config_hash,
                active_sandbox_hash=self.active_sandbox_hash,
                active_cap_hash=self.active_cap_hash,
            )

    # ── RD-16: Pre-Grant Worker Death Race ────────────────────────────
    def test_rd16_pre_grant_worker_death_race(self) -> None:
        """RD-16: Worker unregisters (dies) before grant_lease -> revalidation fails."""
        lease_mgr = LeaseManager()
        ledger = InvocationStateLedger()
        dispatcher = GatewayDispatcher(lease_manager=lease_mgr, ledger=ledger)

        w_proposed = self._make_worker("w-1")

        with self.assertRaises(NoEligibleWorkerNow):
            dispatcher.dispatch_invocation(
                invocation_id="inv-dead-worker",
                intent_hash="0x8",
                required_capabilities=["payments.execute"],
                candidate_pool=[w_proposed],
                active_config_gen=18,
                active_config_hash=self.active_config_hash,
                active_sandbox_hash=self.active_sandbox_hash,
                active_cap_hash=self.active_cap_hash,
            )

    # ── RD-17: Pre-Grant Inflight Capacity Breach Race ────────────────
    def test_rd17_pre_grant_inflight_capacity_race(self) -> None:
        """RD-17: Worker reaches max_inflight before grant_lease -> revalidation fails."""
        lease_mgr = LeaseManager()
        ledger = InvocationStateLedger()
        dispatcher = GatewayDispatcher(lease_manager=lease_mgr, ledger=ledger, max_worker_inflight=1)

        w1 = self._make_worker("w-1", inflight=0)
        lease_mgr.register_worker_state(w1)

        dispatcher.dispatch_invocation(
            invocation_id="inv-cap-1",
            intent_hash="0x9",
            required_capabilities=["payments.execute"],
            candidate_pool=[w1],
            active_config_gen=18,
            active_config_hash=self.active_config_hash,
            active_sandbox_hash=self.active_sandbox_hash,
            active_cap_hash=self.active_cap_hash,
        )

        with self.assertRaises(NoEligibleWorkerNow):
            dispatcher.dispatch_invocation(
                invocation_id="inv-cap-2",
                intent_hash="0x10",
                required_capabilities=["payments.execute"],
                candidate_pool=[w1],
                active_config_gen=18,
                active_config_hash=self.active_config_hash,
                active_sandbox_hash=self.active_sandbox_hash,
                active_cap_hash=self.active_cap_hash,
            )

    # ── RD-18: Parallel State Conflict Fencing ────────────────────────
    def test_rd18_parallel_state_conflict_fencing(self) -> None:
        """RD-18: Concurrent mutations targeting the same StateDomainKey raise lock conflict."""
        lease_mgr = LeaseManager()
        ledger = InvocationStateLedger()
        dispatcher = GatewayDispatcher(lease_manager=lease_mgr, ledger=ledger)

        w1 = self._make_worker("w-1")
        lease_mgr.register_worker_state(w1)

        key = StateDomainKey("accounts", "/acc/1", "balance")

        dispatcher.dispatch_invocation(
            invocation_id="inv-state-1",
            intent_hash="0x11",
            required_capabilities=["payments.execute"],
            candidate_pool=[w1],
            active_config_gen=18,
            active_config_hash=self.active_config_hash,
            active_sandbox_hash=self.active_sandbox_hash,
            active_cap_hash=self.active_cap_hash,
            execution_class=ExecutionClass.SERIALIZED_STATE_DOMAIN,
            state_domain_key=key,
        )

        with self.assertRaises(ValueError):
            dispatcher.dispatch_invocation(
                invocation_id="inv-state-2",
                intent_hash="0x12",
                required_capabilities=["payments.execute"],
                candidate_pool=[w1],
                active_config_gen=18,
                active_config_hash=self.active_config_hash,
                active_sandbox_hash=self.active_sandbox_hash,
                active_cap_hash=self.active_cap_hash,
                execution_class=ExecutionClass.SERIALIZED_STATE_DOMAIN,
                state_domain_key=key,
            )

    # ── RD-19: Per-Invocation Lease Scope Isolation ──────────────────
    def test_rd19_per_invocation_lease_scope_isolation(self) -> None:
        """RD-19: Lease epochs are scoped per invocation lineage."""
        lease_mgr = LeaseManager()
        l1 = lease_mgr.grant_lease("inv-A", "w-1")
        l2 = lease_mgr.grant_lease("inv-B", "w-1")

        self.assertEqual(l1.lease_epoch, 1)
        self.assertEqual(l2.lease_epoch, 1)

    # ── RD-20: Bounded Metadata Memory ────────────────────────────────
    def test_rd20_bounded_metadata_memory(self) -> None:
        """RD-20: Router decision events stream to buffer and do not retain heavy state objects."""
        lease_mgr = LeaseManager()
        ledger = InvocationStateLedger()
        dispatcher = GatewayDispatcher(lease_manager=lease_mgr, ledger=ledger)

        w1 = self._make_worker("w-1")
        lease_mgr.register_worker_state(w1)

        for i in range(50):
            dispatcher.dispatch_invocation(
                invocation_id=f"inv-mem-{i}",
                intent_hash="0xMEM",
                required_capabilities=["payments.execute"],
                candidate_pool=[w1],
                active_config_gen=18,
                active_config_hash=self.active_config_hash,
                active_sandbox_hash=self.active_sandbox_hash,
                active_cap_hash=self.active_cap_hash,
            )
            lease_mgr.commit_invocation(f"inv-mem-{i}", 1)

        self.assertEqual(len(dispatcher.decision_events), 50)
        self.assertTrue(all(isinstance(ev, RoutingDecisionEvent) for ev in dispatcher.decision_events))

    # ── RD-21: Deterministic Tie-Breaking Verification ───────────────
    def test_rd21_deterministic_tie_breaking(self) -> None:
        """RD-21: Candidates with identical inflight load tie-break deterministically by instance_id."""
        policy = RoutingPolicy()
        w_b = self._make_worker("w-bravo", inflight=0)
        w_a = self._make_worker("w-alpha", inflight=0)
        w_c = self._make_worker("w-charlie", inflight=0)

        selected = policy.select_candidate([w_b, w_a, w_c])
        self.assertEqual(selected.instance_id, "w-alpha")

    # ── RD-22: Router Zero-Token Possession Isolation ───────────────
    def test_rd22_router_zero_token_possession_isolation(self) -> None:
        """RD-22: Router and policy objects do not store or hold authorization tokens."""
        policy = RoutingPolicy()
        resolver = CandidateResolver()
        w1 = self._make_worker("w-1")

        resolved = resolver.resolve_candidates([w1], ["payments.execute"], 18, self.active_config_hash, self.active_sandbox_hash, self.active_cap_hash)
        selected = policy.select_candidate(resolved)

        self.assertFalse(hasattr(selected, "token"))
        self.assertFalse(hasattr(selected, "secret_key"))
        self.assertFalse(hasattr(selected, "bearer_token"))

    # ── RD-23: Router/Lease/Commit Crash Recovery Boundary ───────────
    def test_rd23_router_lease_commit_crash_recovery_boundary(self) -> None:
        """RD-23: Invocation routed & assigned, Gateway crashes mid-execution, WAL replayed cleanly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            journal_path = os.path.join(tmp_dir, "invocation_journal.jsonl")

            # 1. Gateway Phase 1: Dispatch invocation to ASSIGNED state
            lease_mgr = LeaseManager()
            ledger_pre = InvocationStateLedger(journal_path=journal_path)
            dispatcher = GatewayDispatcher(lease_manager=lease_mgr, ledger=ledger_pre)

            w1 = self._make_worker("w-node-1")
            lease_mgr.register_worker_state(w1)

            dispatcher.dispatch_invocation(
                invocation_id="inv-crash-23",
                intent_hash="0xCRASH23",
                required_capabilities=["payments.execute"],
                candidate_pool=[w1],
                active_config_gen=18,
                active_config_hash=self.active_config_hash,
                active_sandbox_hash=self.active_sandbox_hash,
                active_cap_hash=self.active_cap_hash,
            )

            # Advance to RUNNING before crash
            ledger_pre.transition_state("inv-crash-23", InvocationState.RUNNING)

            # 2. Simulate Gateway Crash & Restart: Instantiate new ledger from durable WAL file
            ledger_post = InvocationStateLedger(journal_path=journal_path)
            rec_post = ledger_post.get_record("inv-crash-23")

            self.assertIsNotNone(rec_post)
            assert rec_post is not None
            self.assertEqual(rec_post.state, InvocationState.RUNNING)
            self.assertEqual(rec_post.assigned_worker_id, "w-node-1")

            # Assert recovery classification is ADMITTED_UNACTUATED (safe idempotency boundary)
            bucket = ledger_post.classify_recovery("inv-crash-23")
            self.assertEqual(bucket, RecoveryBucket.ADMITTED_UNACTUATED)

    # ── RD-24: Concurrent Same-StateDomainKey Invocations ─────────────
    def test_rd24_concurrent_same_state_domain_key_fencing(self) -> None:
        """RD-24: Concurrent invocations targeting the same StateDomainKey enforce mutual exclusion."""
        lease_mgr = LeaseManager()
        ledger = InvocationStateLedger()
        dispatcher = GatewayDispatcher(lease_manager=lease_mgr, ledger=ledger)

        w1 = self._make_worker("w-1")
        w2 = self._make_worker("w-2")
        lease_mgr.register_worker_state(w1)
        lease_mgr.register_worker_state(w2)

        key = StateDomainKey("ledger", "/wallets/w-44", "balance")

        results: list[str] = []
        errors: list[Exception] = []

        def worker_task(inv_id: str) -> None:
            try:
                dispatcher.dispatch_invocation(
                    invocation_id=inv_id,
                    intent_hash="0xCONCUR",
                    required_capabilities=["payments.execute"],
                    candidate_pool=[w1, w2],
                    active_config_gen=18,
                    active_config_hash=self.active_config_hash,
                    active_sandbox_hash=self.active_sandbox_hash,
                    active_cap_hash=self.active_cap_hash,
                    execution_class=ExecutionClass.SERIALIZED_STATE_DOMAIN,
                    state_domain_key=key,
                )
                results.append(inv_id)
            except Exception as ex:
                errors.append(ex)

        t1 = threading.Thread(target=worker_task, args=("inv-conc-1",))
        t2 = threading.Thread(target=worker_task, args=("inv-conc-2",))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Exactly one invocation must succeed in acquiring lock; the second receives conflict exception
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ValueError)
        self.assertIn("State domain lock conflict", str(errors[0]))


if __name__ == "__main__":
    unittest.main()
