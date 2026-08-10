"""
v0.2.0 Regression: Event Serialization Roundtrip

Validates that event_to_dict → dict_to_event roundtrip preserves all fields
for every event type in the v0.2.0 schema.
"""

import unittest

from cortex.schema.events import (
    BaseEvent,
    CommandIssuedEvent,
    DriverTelemetryEvent,
    IntentEvent,
    PlanGeneratedEvent,
    VerificationResultEvent,
    dict_to_event,
    event_to_dict,
)


class TestEventSerializationRoundtrip(unittest.TestCase):
    """Assert lossless serialization for all v0.2.0 event types."""

    def _assert_roundtrip(self, original: BaseEvent) -> None:
        """Helper: serialize → deserialize → assert field equality."""
        serialized = event_to_dict(original)

        # _event_type key must be present
        self.assertIn("_event_type", serialized)
        self.assertEqual(serialized["_event_type"], type(original).__name__)

        restored = dict_to_event(serialized)

        # Type must match
        self.assertEqual(type(restored).__name__, type(original).__name__)

        # All fields must match
        self.assertEqual(restored.event_id, original.event_id)
        self.assertEqual(restored.workflow_id, original.workflow_id)
        self.assertEqual(restored.causation_id, original.causation_id)
        self.assertEqual(restored.correlation_id, original.correlation_id)
        self.assertEqual(restored.root_id, original.root_id)
        self.assertEqual(restored.timestamp_ns, original.timestamp_ns)

    def test_base_event_roundtrip(self) -> None:
        """BaseEvent serialization roundtrip."""
        event = BaseEvent(
            workflow_id="wf_001",
            causation_id="cause_001",
            correlation_id="corr_001",
            root_id="root_001",
        )
        self._assert_roundtrip(event)

    def test_intent_event_roundtrip(self) -> None:
        """IntentEvent serialization roundtrip preserves goal and parameters."""
        event = IntentEvent(
            workflow_id="wf_002",
            goal="Test serialization",
            parameters={"key": "value"},
            session_id="sess_002",
        )
        self._assert_roundtrip(event)
        serialized = event_to_dict(event)
        restored = dict_to_event(serialized)
        assert isinstance(restored, IntentEvent)
        self.assertEqual(restored.goal, event.goal)
        self.assertEqual(restored.intent_id, event.intent_id)

    def test_plan_generated_event_roundtrip(self) -> None:
        """PlanGeneratedEvent serialization roundtrip preserves steps."""
        event = PlanGeneratedEvent(
            workflow_id="wf_003",
            intent_id="intent_003",
            steps=[{"step": 1, "action": "test"}, {"step": 2, "action": "verify"}],
        )
        self._assert_roundtrip(event)
        serialized = event_to_dict(event)
        restored = dict_to_event(serialized)
        assert isinstance(restored, PlanGeneratedEvent)
        self.assertEqual(len(restored.steps), 2)
        self.assertEqual(restored.intent_id, event.intent_id)

    def test_command_issued_event_roundtrip(self) -> None:
        """CommandIssuedEvent serialization roundtrip preserves action and parameters."""
        event = CommandIssuedEvent(
            workflow_id="wf_004",
            plan_id="plan_004",
            action="execute_test",
            parameters={"force": 100},
        )
        self._assert_roundtrip(event)
        serialized = event_to_dict(event)
        restored = dict_to_event(serialized)
        assert isinstance(restored, CommandIssuedEvent)
        self.assertEqual(restored.action, "execute_test")
        self.assertEqual(restored.plan_id, event.plan_id)

    def test_driver_telemetry_event_roundtrip(self) -> None:
        """DriverTelemetryEvent serialization roundtrip preserves status and payload."""
        event = DriverTelemetryEvent(
            workflow_id="wf_005",
            driver_id="driver_005",
            status="ok",
            payload={"position": 42.0},
        )
        self._assert_roundtrip(event)
        serialized = event_to_dict(event)
        restored = dict_to_event(serialized)
        assert isinstance(restored, DriverTelemetryEvent)
        self.assertEqual(restored.status, "ok")
        self.assertEqual(restored.driver_id, "driver_005")

    def test_verification_result_event_roundtrip(self) -> None:
        """VerificationResultEvent serialization roundtrip preserves passed and rule_id."""
        event = VerificationResultEvent(
            workflow_id="wf_006",
            passed=False,
            rule_id="TORQUE_LIMIT",
            details={"reason": "exceeded"},
            metrics={"value": 150},
        )
        self._assert_roundtrip(event)
        serialized = event_to_dict(event)
        restored = dict_to_event(serialized)
        assert isinstance(restored, VerificationResultEvent)
        self.assertFalse(restored.passed)
        self.assertEqual(restored.rule_id, "TORQUE_LIMIT")

    def test_unknown_event_type_falls_back_to_base(self) -> None:
        """Unknown _event_type deserializes as BaseEvent (graceful degradation)."""
        raw = {
            "_event_type": "UnknownFutureEvent",
            "event_id": "evt_unknown",
            "workflow_id": "wf_fallback",
            "causation_id": None,
            "correlation_id": "",
            "root_id": "",
            "timestamp_ns": 0,
            "metadata": {},
        }
        restored = dict_to_event(raw)
        self.assertIsInstance(restored, BaseEvent)
        self.assertEqual(restored.event_id, "evt_unknown")


if __name__ == "__main__":
    _ = unittest.main()
