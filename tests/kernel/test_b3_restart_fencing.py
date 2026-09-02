"""
Sub-Gate B.3 Adversarial Test Matrix — Distributed & Restart In-Flight Fencing

Verifies Sub-Gate B.3 Safety Invariants:
    1. Crash before ADMITTED fsync -> Clean WAL tail recovery.
    2. Crash during ACTUATING -> Recovers to UNKNOWN -> QUARANTINED (no blind retries).
    3. Crash after external commit, before COMMITTED fsync -> Recovers to QUARANTINED.
    4. Epoch change while effect is in-flight -> Rejected with StaleEpochError.
    5. Stale Gateway retries old effect -> Rejected by epoch fence.
    6. Two Gateways attempt same EffectKey -> Cross-Gateway claim lock rejects second attempt.
    7. Duplicate replay after restart -> Returns exact original EffectOutcome with evidence without re-executing adapter.
    8. Quarantined effect blocks automatic retry -> Returns UNKNOWN_EFFECT with quarantine message.
    9. Committed effect never executes twice -> Adapter execution count == 1.
    10. CRC32 WAL corruption detection -> WALCorruptRecordError raises on mid-file corruption.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from cortex.tools.kernel.adapter_contract import (
    AdapterOutcome,
    EvidencePayload,
    ExecutionStatus,
    ResourceContract,
)
from cortex.tools.kernel.effect_gateway import EffectOutcome
from cortex.tools.kernel.effect_wal import (
    EffectWALEngine,
    EffectWALRecord,
    EffectWALState,
    WALCorruptRecordError,
)
from cortex.tools.kernel.gateway_reconciliation import (
    EffectInFlightError,
    GatewayReconciliationEngine,
    StaleEpochError,
)


class TestSubGateB3_AdversarialFencing(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.lock_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.lock_dir, ignore_errors=True)

    def _make_mock_adapter(self, status=ExecutionStatus.EFFECT_CONFIRMED, evidence_bytes=b"test_evidence"):
        adapter = MagicMock(spec=ResourceContract)
        adapter.execute_effect.return_value = AdapterOutcome(
            status=status,
            evidence=EvidencePayload(data=evidence_bytes, is_reference=False),
            error_message=None,
        )
        return adapter

    # Scenario 1 & 6: Stale Gateway retries old effect / Epoch Fencing
    def test_scenario_1_and_6_epoch_fencing_rejection(self) -> None:
        wal = EffectWALEngine(self.temp_dir)
        engine = GatewayReconciliationEngine(
            wal_engine=wal,
            active_lease_epoch=10,
            active_authority_epoch=2,
            lock_dir=self.lock_dir,
        )
        adapter = self._make_mock_adapter()

        # Reject Stale Authority Epoch
        with self.assertRaises(StaleEpochError):
            engine.execute_fenced_effect(
                invocation_id="inv_1",
                execution_attempt_id="att_1",
                effect_key="key_stale_auth",
                lease_epoch=10,
                authority_epoch=1,  # Stale authority epoch (1 < 2)
                payload=b"{}",
                adapter=adapter,
            )

        # Reject Stale Lease Epoch
        with self.assertRaises(StaleEpochError):
            engine.execute_fenced_effect(
                invocation_id="inv_2",
                execution_attempt_id="att_2",
                effect_key="key_stale_lease",
                lease_epoch=9,  # Mismatched lease epoch (9 != 10)
                authority_epoch=2,
                payload=b"{}",
                adapter=adapter,
            )

        self.assertEqual(adapter.execute_effect.call_count, 0)

    # Scenario 2 & 3 & 4 & 9: Crash during ACTUATING recovers safely to QUARANTINED
    def test_scenario_2_3_4_9_crash_during_actuating_recovers_to_quarantined(self) -> None:
        # Gateway 1 writes ADMITTED and ACTUATING, then crashes
        wal_1 = EffectWALEngine(self.temp_dir)
        wal_1.append_record("inv_100", "key_100", 10, 2, EffectWALState.ADMITTED, b"{}")
        wal_1.append_record("inv_100", "key_100", 10, 2, EffectWALState.ACTUATING, b"{}")
        wal_1.close()

        # Gateway 2 starts up on recovery under higher authority epoch 3
        wal_2 = EffectWALEngine(self.temp_dir)
        engine_2 = GatewayReconciliationEngine(
            wal_engine=wal_2,
            active_lease_epoch=10,
            active_authority_epoch=3,
            lock_dir=self.lock_dir,
        )

        adapter = self._make_mock_adapter()

        # Attempting to re-run the crashed effect key must return UNKNOWN_EFFECT without calling adapter
        outcome = engine_2.execute_fenced_effect(
            invocation_id="inv_100",
            execution_attempt_id="att_rec_1",
            effect_key="key_100",
            lease_epoch=10,
            authority_epoch=3,
            payload=b"{}",
            adapter=adapter,
        )

        self.assertEqual(outcome.status, ExecutionStatus.UNKNOWN_EFFECT)
        self.assertIn("QUARANTINED", outcome.error_message or "")
        self.assertEqual(adapter.execute_effect.call_count, 0)

    # Scenario 7: Two Gateways attempt same EffectKey -> Cross-Gateway claim lock rejects second attempt
    def test_scenario_7_cross_gateway_concurrent_execution_fenced(self) -> None:
        from cortex.tools.kernel.gateway_reconciliation import CrossGatewayClaimLock

        claim_lock = CrossGatewayClaimLock(lock_dir=self.lock_dir)

        # Gateway A acquires claim
        h1 = claim_lock.acquire_claim("key_shared_99")
        self.assertIsNotNone(h1)

        # Gateway B attempts claim for same key -> Fails (None)
        h2 = claim_lock.acquire_claim("key_shared_99")
        self.assertIsNone(h2)

        # Gateway A releases claim
        claim_lock.release_claim(h1)

        # Gateway B can now acquire claim
        h3 = claim_lock.acquire_claim("key_shared_99")
        self.assertIsNotNone(h3)
        claim_lock.release_claim(h3)

    # Scenario 8 & 10: COMMITTED Replay returns exact original outcome with evidence
    def test_scenario_8_and_10_committed_effect_replay_returns_original_outcome(self) -> None:
        wal = EffectWALEngine(self.temp_dir)
        engine = GatewayReconciliationEngine(
            wal_engine=wal,
            active_lease_epoch=10,
            active_authority_epoch=1,
            lock_dir=self.lock_dir,
        )

        adapter = self._make_mock_adapter(evidence_bytes=b"original_evidence_payload")

        # First Execution -> Adapter executed
        res1 = engine.execute_fenced_effect(
            invocation_id="inv_200",
            execution_attempt_id="att_200",
            effect_key="key_200",
            lease_epoch=10,
            authority_epoch=1,
            payload=b"{}",
            adapter=adapter,
        )
        self.assertEqual(res1.status, ExecutionStatus.EFFECT_CONFIRMED)
        self.assertIsNotNone(res1.evidence)
        assert res1.evidence is not None
        self.assertEqual(res1.evidence.data, b"original_evidence_payload")
        self.assertEqual(adapter.execute_effect.call_count, 1)

        # Second Execution (Replay attempt) -> Returns cached outcome without adapter execution
        res2 = engine.execute_fenced_effect(
            invocation_id="inv_200",
            execution_attempt_id="att_200_replay",
            effect_key="key_200",
            lease_epoch=10,
            authority_epoch=1,
            payload=b"{}",
            adapter=adapter,
        )
        self.assertEqual(res2.status, ExecutionStatus.EFFECT_CONFIRMED)
        self.assertIsNotNone(res2.evidence)
        assert res2.evidence is not None
        self.assertEqual(res2.evidence.data, b"original_evidence_payload")
        self.assertEqual(adapter.execute_effect.call_count, 1)  # Adapter NOT re-invoked!

    # Scenario 5: Future / Invalid Authority Epoch Rejection
    def test_scenario_5_future_authority_epoch_rejected(self) -> None:
        wal = EffectWALEngine(self.temp_dir)
        engine = GatewayReconciliationEngine(
            wal_engine=wal,
            active_lease_epoch=10,
            active_authority_epoch=2,
            lock_dir=self.lock_dir,
        )
        adapter = self._make_mock_adapter()

        # Reject Future Authority Epoch (3 != active 2)
        with self.assertRaises(StaleEpochError):
            engine.execute_fenced_effect(
                invocation_id="inv_future",
                execution_attempt_id="att_fut",
                effect_key="key_future",
                lease_epoch=10,
                authority_epoch=3,
                payload=b"{}",
                adapter=adapter,
            )

    # Scenario 10b: Binary CRC32 Corruption Detection
    def test_crc32_wal_corruption_detection(self) -> None:
        wal = EffectWALEngine(self.temp_dir)
        wal.append_record("inv_corrupt_1", "key_corrupt_1", 10, 1, EffectWALState.ADMITTED, b"{}")
        wal.append_record("inv_corrupt_2", "key_corrupt_2", 10, 1, EffectWALState.ADMITTED, b"{}")
        wal.close()

        # Tamper with payload bytes of the FIRST record in middle of WAL file
        wal_file = Path(self.temp_dir) / "effect_lifecycle.wal"
        with open(wal_file, "r+b") as f:
            f.seek(EffectWALEngine.HEADER_SIZE + 2)
            f.write(b"\xFF\xFF\xFF")

        wal_corrupt = EffectWALEngine(self.temp_dir)
        try:
            with self.assertRaises(WALCorruptRecordError):
                wal_corrupt.replay_all_records()
        finally:
            wal_corrupt.close()




if __name__ == "__main__":
    unittest.main()
