"""
Issue #34 (Phase 6.1.1 Gate): Write-Ahead Log (WAL) Crash & Corruption Adversarial Test Suite
Normative Target: v1.5.1-FINAL-FROZEN
Proof Target: Replay(WAL_corrupt) == State_last_valid
"""

import os
import shutil
import tempfile
import unittest

from cortex.tools.kernel.durable_state import (
    DurableStateStore,
    WALRecord,
    WALRecordType,
)


class TestPhase6WALAdversarialGate(unittest.TestCase):
    """Phase 6.1.1 WAL Crash & Corruption Adversarial Verification Gate."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir)

    def test_partial_header_write_recovery(self) -> None:
        """Truncated header write (e.g. 10 of 20 bytes written) stops replay cleanly at last valid record."""
        store = DurableStateStore(self.test_dir)
        store.append_record(
            WALRecordType.REGISTER_WORKER,
            timestamp_ms=100,
            data={"worker_id": "w1", "max_concurrency": 5},
        )
        store.close()

        # Append partial 10-byte truncated header
        wal_path = store.wal_file_path
        with open(wal_path, "ab") as f:
            f.write(b"CWAL_PARTI")

        store_recovery = DurableStateStore(self.test_dir)
        replayed = store_recovery.replay_all_records()
        self.assertEqual(len(replayed), 1)
        self.assertEqual(replayed[0].seq_no, 1)
        self.assertEqual(replayed[0].data["worker_id"], "w1")
        store_recovery.close()

    def test_partial_payload_write_recovery(self) -> None:
        """Truncated payload write stops replay cleanly at last valid record."""
        store = DurableStateStore(self.test_dir)
        store.append_record(
            WALRecordType.REGISTER_WORKER,
            timestamp_ms=100,
            data={"worker_id": "w1", "max_concurrency": 5},
        )
        store.append_record(
            WALRecordType.ASSIGN_EXECUTION,
            timestamp_ms=105,
            data={"invocation_id": "inv_1", "worker_id": "w1", "lease_epoch": 1},
        )
        store.close()

        # Truncate wal file in middle of second record payload
        wal_path = store.wal_file_path
        full_size = os.path.getsize(wal_path)
        with open(wal_path, "r+b") as f:
            f.truncate(full_size - 10)  # Cut off last 10 bytes of payload

        store_recovery = DurableStateStore(self.test_dir)
        replayed = store_recovery.replay_all_records()
        self.assertEqual(len(replayed), 1)
        self.assertEqual(replayed[0].seq_no, 1)
        store_recovery.close()

    def test_crc32_payload_bit_flip_detection(self) -> None:
        """Bit flip in payload CRC triggers WALCorruptRecordError or clean containment at last valid record."""
        store = DurableStateStore(self.test_dir)
        store.append_record(
            WALRecordType.LEADER_EPOCH_ADVANCE,
            timestamp_ms=100,
            data={"leader_epoch": 1},
        )
        store.close()

        # Corrupt 1 byte in middle of payload
        wal_path = store.wal_file_path
        with open(wal_path, "r+b") as f:
            f.seek(DurableStateStore.HEADER_SIZE + 2)
            corrupt_byte = bytes([f.read(1)[0] ^ 0xFF])
            f.seek(DurableStateStore.HEADER_SIZE + 2)
            f.write(corrupt_byte)

        store_recovery = DurableStateStore(self.test_dir)
        replayed = store_recovery.replay_all_records()
        # Corrupted record 1 rejected -> 0 records recovered
        self.assertEqual(len(replayed), 0)
        store_recovery.close()

    def test_sequence_number_gap_and_rollback_protection(self) -> None:
        """Out-of-order or duplicate sequence numbers stop replay safely at last valid record."""
        store = DurableStateStore(self.test_dir)
        store.append_record(
            WALRecordType.REGISTER_WORKER,
            timestamp_ms=100,
            data={"worker_id": "w1", "max_concurrency": 5},
        )
        store.close()

        # Manually append a record with wrong sequence number (seq_no=5 instead of expected 2)
        out_of_order_rec = WALRecord(
            seq_no=5,
            record_type=WALRecordType.ASSIGN_EXECUTION,
            timestamp_ms=200,
            data={"invocation_id": "inv_bad", "worker_id": "w1", "lease_epoch": 1},
        )
        wal_path = store.wal_file_path
        with open(wal_path, "ab") as f:
            f.write(out_of_order_rec.serialize())

        store_recovery = DurableStateStore(self.test_dir)
        replayed = store_recovery.replay_all_records()
        self.assertEqual(len(replayed), 1)
        self.assertEqual(replayed[0].seq_no, 1)
        store_recovery.close()

    def test_trailing_garbage_resilience(self) -> None:
        """Arbitrary garbage bytes appended after valid records leave valid history intact."""
        store = DurableStateStore(self.test_dir)
        store.append_record(
            WALRecordType.REGISTER_WORKER,
            timestamp_ms=100,
            data={"worker_id": "w1", "max_concurrency": 5},
        )
        store.close()

        wal_path = store.wal_file_path
        with open(wal_path, "ab") as f:
            f.write(os.urandom(256))

        store_recovery = DurableStateStore(self.test_dir)
        replayed = store_recovery.replay_all_records()
        self.assertEqual(len(replayed), 1)
        self.assertEqual(replayed[0].seq_no, 1)
        store_recovery.close()

    def test_repeated_open_replay_close_cycles(self) -> None:
        """1,000 append-replay-close cycles verify continuous sequence progression and zero leak."""
        for i in range(1, 1001):
            store = DurableStateStore(self.test_dir)
            replayed = store.replay_all_records()
            self.assertEqual(len(replayed), i - 1)
            rec = store.append_record(
                WALRecordType.ASSIGN_EXECUTION,
                timestamp_ms=1000 + i,
                data={"invocation_id": f"inv_{i}", "worker_id": "w1", "lease_epoch": i},
            )
            self.assertEqual(rec.seq_no, i)
            store.close()

        final_store = DurableStateStore(self.test_dir)
        final_replayed = final_store.replay_all_records()
        self.assertEqual(len(final_replayed), 1000)
        self.assertEqual(final_replayed[-1].seq_no, 1000)
        final_store.close()


if __name__ == "__main__":
    unittest.main()
