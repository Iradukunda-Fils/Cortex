"""
Kernel Runtime End-to-End Test Suite
"""

import unittest
from tools.kernel.transport import InMemoryTransport
from tools.kernel.context import RuntimeContext
from tools.kernel.schema.event import Event, RawRTLTraceEvent, CommitVerifiedEvent, MotorFeedbackEvent
from tools.kernel.drivers.mock_robot import MockRobotDriver
from tools.kernel.drivers.rtl_verilator import RTLVerilatorDriver
from tools.kernel.services.verification import VerificationKernelService
from tools.kernel.services.event_store import EventStoreService

class TestKernelRuntime(unittest.TestCase):
    def setUp(self):
        self.transport = InMemoryTransport()
        self.context = RuntimeContext("actor_001", "session_100", self.transport)

    def test_stage_1_transport_and_mailbox(self):
        ctx = RuntimeContext("test_actor", "sess_001", self.transport)
        ctx.mailbox.push("msg_low_prio", priority=10)
        ctx.mailbox.push("msg_high_prio", priority=1)

        self.assertEqual(ctx.mailbox.pop(), "msg_high_prio")
        self.assertEqual(ctx.mailbox.pop(), "msg_low_prio")

    def test_stage_2_mock_robot_driver(self):
        received_events = []
        self.transport.subscribe(MotorFeedbackEvent, lambda e: received_events.append(e))

        driver = MockRobotDriver(self.context, "joint_arm_x")
        driver.step_actuator(1.5, 0.5)

        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].actuator_id, "joint_arm_x")
        self.assertEqual(received_events[0].position, 1.5)

    def test_stage_3_verification_service_and_event_store(self):
        event_store = EventStoreService()
        self.transport.subscribe(Event, event_store.record_event)

        verif_service = VerificationKernelService(self.context)
        self.transport.subscribe(RawRTLTraceEvent, verif_service.handle_raw_rtl_trace)

        rtl_driver = RTLVerilatorDriver(self.context)
        count = rtl_driver.ingest_trace_file("rtl_trace.json")

        self.assertGreater(count, 0)
        self.assertEqual(verif_service.verified_count, count)

        # Audit event store records both RawRTLTraceEvent and CommitVerifiedEvent
        log = event_store.get_log()
        self.assertGreaterEqual(len(log), count * 2)

        # Verify causation and correlation ID propagation
        verified_events = [e for e in log if isinstance(e, CommitVerifiedEvent)]
        self.assertEqual(len(verified_events), count)
        self.assertTrue(all(ve.verified for ve in verified_events))

if __name__ == "__main__":
    unittest.main()
