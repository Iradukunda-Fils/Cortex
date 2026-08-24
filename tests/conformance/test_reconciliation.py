"""
Conformance tests for EffectReconciliationEngine and Layered Quarantine Machine (Issue #45)
"""

import unittest

from cortex.tools.kernel.adapter_contract import (
    AdapterExecutionContext,
    AdapterOutcome,
    EffectClassification,
    ExecutionStatus,
)
from cortex.tools.kernel.reconciliation import (
    EffectReconciliationEngine,
    IndeterminateEffectError,
    InvocationState,
    QuarantinedResourceError,
)


class MockWitnessProbe:
    """Mock witness probe implementation."""

    def __init__(self, expected_status: ExecutionStatus) -> None:
        self.expected_status = expected_status

    def probe_status(self, ctx: AdapterExecutionContext) -> ExecutionStatus:
        return self.expected_status


class TestEffectReconciliationEngine(unittest.TestCase):
    """Test suite for Issue #45 Effect Reconciliation Engine & Layered Quarantine Machine."""

    def setUp(self) -> None:
        self.engine = EffectReconciliationEngine()
        self.ctx = AdapterExecutionContext(
            invocation_id="inv_rec_100",
            execution_attempt_id="att_1",
            adapter_request_id="req_100",
            idempotency_key="hmac-sha256:v1:test_key",
            lease_epoch=1,
            resource_id="db://payments/charge_99",
            operation_type="CHARGE_CREDIT_CARD",
        )

    def test_layer1_confirmed_outcome(self) -> None:
        outcome = AdapterOutcome(status=ExecutionStatus.EFFECT_CONFIRMED)
        state = self.engine.reconcile_effect(
            ctx=self.ctx,
            classification=EffectClassification.NON_IDEMPOTENT_WRITE,
            outcome=outcome,
        )
        self.assertEqual(state, InvocationState.CONFIRMED)
        self.assertFalse(self.engine.is_resource_quarantined("db://payments/charge_99"))

    def test_layer1_not_applied_outcome(self) -> None:
        outcome = AdapterOutcome(status=ExecutionStatus.EFFECT_NOT_APPLIED)
        state = self.engine.reconcile_effect(
            ctx=self.ctx,
            classification=EffectClassification.NON_IDEMPOTENT_WRITE,
            outcome=outcome,
        )
        self.assertEqual(state, InvocationState.NOT_APPLIED)
        self.assertFalse(self.engine.is_resource_quarantined("db://payments/charge_99"))

    def test_idempotent_write_unknown_effect_safe_retry(self) -> None:
        # Idempotent write with UNKNOWN_EFFECT returns NOT_APPLIED for safe retry
        outcome = AdapterOutcome(status=ExecutionStatus.UNKNOWN_EFFECT)
        state = self.engine.reconcile_effect(
            ctx=self.ctx,
            classification=EffectClassification.IDEMPOTENT_WRITE,
            outcome=outcome,
        )
        self.assertEqual(state, InvocationState.NOT_APPLIED)
        self.assertFalse(self.engine.is_resource_quarantined("db://payments/charge_99"))

    def test_layer2_witness_probe_resolves_unknown_effect(self) -> None:
        outcome = AdapterOutcome(status=ExecutionStatus.UNKNOWN_EFFECT)
        witness = MockWitnessProbe(expected_status=ExecutionStatus.EFFECT_CONFIRMED)

        state = self.engine.reconcile_effect(
            ctx=self.ctx,
            classification=EffectClassification.NON_IDEMPOTENT_WRITE,
            outcome=outcome,
            witness_probe=witness,
        )
        self.assertEqual(state, InvocationState.CONFIRMED)
        self.assertFalse(self.engine.is_resource_quarantined("db://payments/charge_99"))

    def test_layer3_non_idempotent_unknown_effect_triggers_quarantine(self) -> None:
        outcome = AdapterOutcome(status=ExecutionStatus.UNKNOWN_EFFECT)

        with self.assertRaises(IndeterminateEffectError):
            self.engine.reconcile_effect(
                ctx=self.ctx,
                classification=EffectClassification.NON_IDEMPOTENT_WRITE,
                outcome=outcome,
            )

        self.assertTrue(self.engine.is_resource_quarantined("db://payments/charge_99"))
        record = self.engine.get_quarantine_record("db://payments/charge_99")
        self.assertIsNotNone(record)
        self.assertEqual(record.invocation_id, "inv_rec_100")
        self.assertEqual(record.execution_attempt_id, "att_1")

    def test_quarantined_resource_blocks_subsequent_executions(self) -> None:
        outcome = AdapterOutcome(status=ExecutionStatus.UNKNOWN_EFFECT)
        try:
            self.engine.reconcile_effect(
                ctx=self.ctx,
                classification=EffectClassification.NON_IDEMPOTENT_WRITE,
                outcome=outcome,
            )
        except IndeterminateEffectError:
            pass

        # Subsequent execution attempt on quarantined resource raises QuarantinedResourceError
        new_ctx = AdapterExecutionContext(
            invocation_id="inv_rec_101",
            execution_attempt_id="att_1",
            adapter_request_id="req_101",
            idempotency_key="hmac-sha256:v1:test_key_2",
            lease_epoch=1,
            resource_id="db://payments/charge_99",  # Quarantined resource
            operation_type="CHARGE_CREDIT_CARD",
        )
        with self.assertRaises(QuarantinedResourceError):
            self.engine.reconcile_effect(
                ctx=new_ctx,
                classification=EffectClassification.NON_IDEMPOTENT_WRITE,
                outcome=AdapterOutcome(status=ExecutionStatus.EFFECT_CONFIRMED),
            )

    def test_operator_lift_quarantine_unblocks_resource(self) -> None:
        outcome = AdapterOutcome(status=ExecutionStatus.UNKNOWN_EFFECT)
        try:
            self.engine.reconcile_effect(
                ctx=self.ctx,
                classification=EffectClassification.NON_IDEMPOTENT_WRITE,
                outcome=outcome,
            )
        except IndeterminateEffectError:
            pass

        # Operator lifts quarantine
        self.engine.lift_quarantine("db://payments/charge_99", operator_reason="Manual verification completed")
        self.assertFalse(self.engine.is_resource_quarantined("db://payments/charge_99"))

        # Subsequent execution now succeeds
        state = self.engine.reconcile_effect(
            ctx=self.ctx,
            classification=EffectClassification.NON_IDEMPOTENT_WRITE,
            outcome=AdapterOutcome(status=ExecutionStatus.EFFECT_CONFIRMED),
        )
        self.assertEqual(state, InvocationState.CONFIRMED)


if __name__ == "__main__":
    unittest.main()
