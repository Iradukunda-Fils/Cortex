"""
Issue #34 (Phase 6.1): Durable State Engine & Write-Ahead Logging (WAL) Test Suite
Coq Target: Phase4RoutingRefinement.v
"""

import shutil
import tempfile
import unittest

from cortex.tools.kernel.durable_state import (
    DurableStateStore,
    WALCorruptRecordError,
    WALRecord,
    WALRecordType,
)


class TestPhase6DurableStateStore(unittest.TestCase):
    """Phase 6.1 WAL Engine and Recovery Test Suite."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir)

    def test_wal_record_serialization_integrity(self) -> None:
        """Verifies binary serialization and CRC32 checksum verification."""
        record = WALRecord(
            seq_no=1,
            record_type=WALRecordType.ASSIGN_EXECUTION,
            timestamp_ms=1700000000000,
            data={"invocation_id": "inv_1", "worker_id": "w1", "lease_epoch": 5},
        )

        serialized = record.serialize()
        header = serialized[: DurableStateStore.HEADER_SIZE]
        payload = serialized[DurableStateStore.HEADER_SIZE :]

        deserialized = WALRecord.deserialize(header, payload)
        self.assertEqual(deserialized.seq_no, 1)
        self.assertEqual(deserialized.record_type, WALRecordType.ASSIGN_EXECUTION)
        self.assertEqual(deserialized.data["invocation_id"], "inv_1")

        # Corrupt single byte in payload -> deserialization MUST raise WALCorruptRecordError
        corrupted_payload = bytearray(payload)
        corrupted_payload[0] ^= 0xFF
        with self.assertRaises(WALCorruptRecordError):
            WALRecord.deserialize(header, bytes(corrupted_payload))

    def test_wal_append_and_crash_recovery_replay(self) -> None:
        """Simulates node crash and restart by replaying WAL logs."""
        store1 = DurableStateStore(self.test_dir)
        store1.append_record(
            WALRecordType.REGISTER_WORKER,
            timestamp_ms=1000,
            data={"worker_id": "w1", "max_concurrency": 5},
        )
        store1.append_record(
            WALRecordType.ASSIGN_EXECUTION,
            timestamp_ms=1005,
            data={"invocation_id": "inv_999", "worker_id": "w1", "lease_epoch": 1},
        )
        store1.close()

        # Simulate process crash & new node startup
        store2 = DurableStateStore(self.test_dir)
        replayed = store2.replay_all_records()

        self.assertEqual(len(replayed), 2)
        self.assertEqual(replayed[0].record_type, WALRecordType.REGISTER_WORKER)
        self.assertEqual(replayed[1].record_type, WALRecordType.ASSIGN_EXECUTION)
        self.assertEqual(replayed[1].data["lease_epoch"], 1)
        self.assertEqual(store2._next_seq_no, 3)
        store2.close()

    def test_wal_truncated_crash_recovery(self) -> None:
        """Verifies that trailing un-synced/partial writes are safely ignored during replay."""
        store = DurableStateStore(self.test_dir)
        r1 = store.append_record(
            WALRecordType.LEADER_EPOCH_ADVANCE,
            timestamp_ms=2000,
            data={"leader_epoch": 10},
        )
        store.close()

        # Append partial garbage bytes to end of WAL file to simulate power loss during disk write
        wal_path = store.wal_file_path
        with open(wal_path, "ab") as f:
            f.write(b"CWAL_PARTIAL_GARBAGE_BYTES")

        store_recovery = DurableStateStore(self.test_dir)
        replayed = store_recovery.replay_all_records()

        self.assertEqual(len(replayed), 1)
        self.assertEqual(replayed[0].data["leader_epoch"], 10)
        store_recovery.close()


if __name__ == "__main__":
    unittest.main()
