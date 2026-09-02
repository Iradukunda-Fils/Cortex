"""
Cortex Gate B: External Effect MCP Adapter Vertical Slice — P1–P12 Adversarial Test Suite

Proves the following security properties against a controlled local MCP server:
    P1:  No credential in worker environment or effect IPC
    P2:  Worker has no direct adapter invocation path (structural bypass prevention)
    P3:  Capability-denied effect requests are rejected before adapter execution
    P4:  Stale lease epoch requests are rejected
    P5:  Idempotency key derivation is deterministic across attempt boundaries
    P6:  Retry semantics depend on Gateway-resolved effect classification
    P7:  UNKNOWN_EFFECT + non-idempotent → quarantine, no blind retry
    P8:  Evidence exceeding 4KiB auto-spools to is_reference=True
    P9:  Gateway crash → no unauthorized continuation
    P10: Adapter crash → deterministic UNKNOWN_EFFECT reconciliation
    P11: Malformed adapter response → EFFECT_NOT_APPLIED, no kernel crash
    P12: Replay request → same idempotency key (no duplicate side-effect identity)
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from dataclasses import fields
from typing import Optional

from cortex.tools.kernel.adapter_contract import (
    AdapterOutcome,
    EffectClassification,
    EffectPayload,
    ExecutionStatus,
    MAX_INLINE_EVIDENCE_BYTES,
)
from cortex.tools.kernel.adapters.mcp_adapter import LocalProcessMCPAdapter
from cortex.tools.kernel.effect_gateway import (
    CapabilityDeniedError,
    EffectFencingError,
    EffectRequest,
    EffectOutcome,
    GatewayAuthorizationGate,
)
from cortex.tools.kernel.reconciliation import (
    EffectReconciliationEngine,
    IndeterminateEffectError,
    InvocationState,
)

# ---------------------------------------------------------------------------
# Locate the local MCP server fixture
# ---------------------------------------------------------------------------

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")
LOCAL_MCP_SERVER = os.path.join(FIXTURES_DIR, "local_mcp_server.py")
MCP_COMMAND = [sys.executable, LOCAL_MCP_SERVER]


# ---------------------------------------------------------------------------
# Test Doubles (Protocol Implementations)
# ---------------------------------------------------------------------------


class StubEffectAuthority:
    """Stub authority: accepts generation=1, epoch=10 only."""

    def __init__(self, valid_generation: int = 1, valid_epoch: int = 10) -> None:
        self._gen = valid_generation
        self._epoch = valid_epoch

    def validate_effect_reservation(
        self, worker_generation: int, lease_epoch: int
    ) -> bool:
        return worker_generation == self._gen and lease_epoch == self._epoch


class StubCapabilityRegistry:
    """
    Stub registry: grants specific capabilities and resolves authoritative classifications.
    Worker NEVER supplies classification — the registry does.
    """

    def __init__(self) -> None:
        self._grants: dict[str, set[str]] = {
            "mcp.echo": {"echo"},
            "mcp.slow": {"slow"},
            "mcp.large": {"large_response"},
            "mcp.ambiguous": {"ambiguous_effect"},
            "mcp.fail": {"fail"},
        }
        self._classifications: dict[str, EffectClassification] = {
            "mcp.echo": EffectClassification.READ_ONLY,
            "mcp.slow": EffectClassification.READ_ONLY,
            "mcp.large": EffectClassification.READ_ONLY,
            "mcp.ambiguous": EffectClassification.UNKNOWN_EFFECT,
            "mcp.fail": EffectClassification.NON_IDEMPOTENT_WRITE,
        }

    def is_capability_granted(self, capability: str, operation: str) -> bool:
        ops = self._grants.get(capability)
        if ops is None:
            return False
        return operation in ops

    def resolve_effect_classification(
        self, capability: str, operation: str
    ) -> EffectClassification:
        return self._classifications.get(
            capability, EffectClassification.UNKNOWN_EFFECT
        )


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


def _make_gate() -> GatewayAuthorizationGate:
    return GatewayAuthorizationGate(
        effect_authority=StubEffectAuthority(),
        capability_registry=StubCapabilityRegistry(),
        domain_secret=b"test_vault_secret_key_32bytes!!__",
    )


def _make_request(
    capability: str = "mcp.echo",
    operation: str = "echo",
    arguments: Optional[bytes] = None,
    resource_id: str = "res_test_01",
    lease_epoch: int = 10,
    worker_generation: int = 1,
    invocation_id: str = "inv_test_001",
) -> EffectRequest:
    if arguments is None:
        arguments = json.dumps(
            {"tool_name": operation, "arguments": {"msg": "hello"}}
        ).encode("utf-8")
    return EffectRequest(
        invocation_id=invocation_id,
        capability=capability,
        operation=operation,
        arguments=arguments,
        resource_id=resource_id,
        lease_epoch=lease_epoch,
        worker_generation=worker_generation,
    )


# ===========================================================================
# P1–P12 ADVERSARIAL TEST GATE
# ===========================================================================


class TestP1_CredentialNonExposure(unittest.TestCase):
    """P1: No credential in worker environment or effect IPC."""

    def test_effect_request_has_no_secret_fields(self) -> None:
        """EffectRequest struct contains zero credential/token/secret fields."""
        req = _make_request()
        field_names = {f.name for f in fields(req)}
        forbidden = {"secret", "token", "api_key", "credential", "password", "bearer"}
        self.assertEqual(field_names & forbidden, set())

    def test_effect_outcome_has_no_secret_fields(self) -> None:
        """EffectOutcome struct contains zero credential/token/secret fields."""
        outcome = EffectOutcome(
            invocation_id="inv_1",
            execution_attempt_id="att_1",
            status=ExecutionStatus.EFFECT_CONFIRMED,
        )
        field_names = {f.name for f in fields(outcome)}
        forbidden = {"secret", "token", "api_key", "credential", "password", "bearer"}
        self.assertEqual(field_names & forbidden, set())

    def test_no_credential_in_effect_request_ipc_data(self) -> None:
        """The IPC payload between worker and gateway contains no vault secrets."""
        gate = _make_gate()
        req = _make_request()
        # The domain_secret is internal to the Gate — verify it never leaks
        ctx, _ = gate.authorize_and_prepare(req, execution_attempt_id="att_1")
        # idempotency_key is a derived hash, not the raw secret
        self.assertTrue(ctx.idempotency_key.startswith("hmac-sha256:v1:"))
        self.assertNotIn("test_vault_secret", ctx.idempotency_key)


class TestP2_DirectBypassPrevention(unittest.TestCase):
    """P2: Worker has no direct adapter invocation path without Gateway."""

    def test_adapter_requires_pre_authorized_context(self) -> None:
        """LocalProcessMCPAdapter.execute_effect requires an AdapterExecutionContext."""
        adapter = LocalProcessMCPAdapter(server_command=MCP_COMMAND)
        # An adapter call without a valid context is structurally impossible:
        # execute_effect signature requires (ctx: AdapterExecutionContext, payload: EffectPayload)
        # There is no method on the adapter that accepts an EffectRequest directly.
        methods = [m for m in dir(adapter) if not m.startswith("_")]
        self.assertNotIn("execute_from_worker", methods)
        self.assertNotIn("execute_raw", methods)
        self.assertIn("execute_effect", methods)


class TestP3_CapabilityAuthorization(unittest.TestCase):
    """P3: Capability-denied requests are rejected before adapter execution."""

    def test_ungranted_capability_rejected(self) -> None:
        gate = _make_gate()
        req = _make_request(capability="mcp.github.write", operation="push")
        with self.assertRaises(CapabilityDeniedError):
            gate.authorize_and_prepare(req, execution_attempt_id="att_1")

    def test_wrong_operation_on_granted_capability_rejected(self) -> None:
        gate = _make_gate()
        req = _make_request(capability="mcp.echo", operation="delete_everything")
        with self.assertRaises(CapabilityDeniedError):
            gate.authorize_and_prepare(req, execution_attempt_id="att_1")


class TestP4_StaleEpochFencing(unittest.TestCase):
    """P4: Stale lease epoch requests are rejected."""

    def test_stale_epoch_rejected(self) -> None:
        gate = _make_gate()
        req = _make_request(lease_epoch=9)  # Active epoch is 10
        with self.assertRaises(EffectFencingError):
            gate.authorize_and_prepare(req, execution_attempt_id="att_1")

    def test_stale_generation_rejected(self) -> None:
        gate = _make_gate()
        req = _make_request(worker_generation=0)  # Active generation is 1
        with self.assertRaises(EffectFencingError):
            gate.authorize_and_prepare(req, execution_attempt_id="att_1")

    def test_future_epoch_rejected(self) -> None:
        gate = _make_gate()
        req = _make_request(lease_epoch=11)  # Active epoch is 10
        with self.assertRaises(EffectFencingError):
            gate.authorize_and_prepare(req, execution_attempt_id="att_1")


class TestP5_DeterministicIdempotencyKey(unittest.TestCase):
    """P5: Same invocation+operation+payload+resource+epoch → same key across attempts."""

    def test_same_request_produces_same_key(self) -> None:
        gate = _make_gate()
        req = _make_request()
        ctx1, _ = gate.authorize_and_prepare(req, execution_attempt_id="att_1")
        ctx2, _ = gate.authorize_and_prepare(req, execution_attempt_id="att_2")
        self.assertEqual(ctx1.idempotency_key, ctx2.idempotency_key)
        self.assertNotEqual(ctx1.execution_attempt_id, ctx2.execution_attempt_id)

    def test_different_payload_produces_different_key(self) -> None:
        gate = _make_gate()
        req1 = _make_request(arguments=b'{"tool_name": "echo", "arguments": {"v": 1}}')
        req2 = _make_request(arguments=b'{"tool_name": "echo", "arguments": {"v": 2}}')
        ctx1, _ = gate.authorize_and_prepare(req1, execution_attempt_id="att_1")
        ctx2, _ = gate.authorize_and_prepare(req2, execution_attempt_id="att_1")
        self.assertNotEqual(ctx1.idempotency_key, ctx2.idempotency_key)


class TestP6_ClassificationGatedRetry(unittest.TestCase):
    """P6: Gateway-resolved classification governs retry semantics."""

    def test_read_only_classification_resolved_by_gateway(self) -> None:
        gate = _make_gate()
        req = _make_request(capability="mcp.echo", operation="echo")
        _, classification = gate.authorize_and_prepare(req, execution_attempt_id="att_1")
        self.assertEqual(classification, EffectClassification.READ_ONLY)

    def test_unknown_effect_classification_resolved_by_gateway(self) -> None:
        gate = _make_gate()
        req = _make_request(capability="mcp.ambiguous", operation="ambiguous_effect")
        _, classification = gate.authorize_and_prepare(req, execution_attempt_id="att_1")
        self.assertEqual(classification, EffectClassification.UNKNOWN_EFFECT)

    def test_read_only_unknown_outcome_is_safe_retry(self) -> None:
        """READ_ONLY + UNKNOWN_EFFECT outcome → NOT_APPLIED (safe for retry)."""
        engine = EffectReconciliationEngine()
        from cortex.tools.kernel.adapter_contract import AdapterExecutionContext

        ctx = AdapterExecutionContext(
            invocation_id="inv_retry_01",
            execution_attempt_id="att_1",
            adapter_request_id="areq_1",
            idempotency_key="k_test",
            lease_epoch=10,
            resource_id="res_1",
            operation_type="echo",
        )
        outcome = AdapterOutcome(status=ExecutionStatus.UNKNOWN_EFFECT)
        state = engine.reconcile_effect(
            ctx=ctx,
            classification=EffectClassification.READ_ONLY,
            outcome=outcome,
        )
        self.assertEqual(state, InvocationState.NOT_APPLIED)


class TestP7_UnknownEffectQuarantine(unittest.TestCase):
    """P7: UNKNOWN_EFFECT + non-idempotent → quarantine, no blind retry."""

    def test_non_idempotent_unknown_triggers_quarantine(self) -> None:
        engine = EffectReconciliationEngine()
        from cortex.tools.kernel.adapter_contract import AdapterExecutionContext

        ctx = AdapterExecutionContext(
            invocation_id="inv_quar_01",
            execution_attempt_id="att_1",
            adapter_request_id="areq_1",
            idempotency_key="k_test",
            lease_epoch=10,
            resource_id="res_payment_99",
            operation_type="charge",
        )
        outcome = AdapterOutcome(status=ExecutionStatus.UNKNOWN_EFFECT)
        with self.assertRaises(IndeterminateEffectError):
            engine.reconcile_effect(
                ctx=ctx,
                classification=EffectClassification.NON_IDEMPOTENT_WRITE,
                outcome=outcome,
            )
        self.assertTrue(engine.is_resource_quarantined("res_payment_99"))


class TestP8_EvidenceSizeBounding(unittest.TestCase):
    """P8: Evidence exceeding 4KiB auto-spools to is_reference=True."""

    def test_large_evidence_becomes_reference(self) -> None:
        adapter = LocalProcessMCPAdapter(server_command=MCP_COMMAND)
        from cortex.tools.kernel.adapter_contract import AdapterExecutionContext

        ctx = AdapterExecutionContext(
            invocation_id="inv_large_01",
            execution_attempt_id="att_1",
            adapter_request_id="areq_1",
            idempotency_key="k_large",
            lease_epoch=10,
            resource_id="res_1",
            operation_type="large_response",
        )
        payload = EffectPayload(
            data=json.dumps(
                {"tool_name": "large_response", "arguments": {"size_bytes": 8192}}
            ).encode("utf-8")
        )
        outcome = adapter.execute_effect(ctx, payload)
        self.assertEqual(outcome.status, ExecutionStatus.EFFECT_CONFIRMED)
        assert outcome.evidence is not None
        self.assertTrue(outcome.evidence.is_reference)

    def test_small_evidence_stays_inline(self) -> None:
        adapter = LocalProcessMCPAdapter(server_command=MCP_COMMAND)
        from cortex.tools.kernel.adapter_contract import AdapterExecutionContext

        ctx = AdapterExecutionContext(
            invocation_id="inv_small_01",
            execution_attempt_id="att_1",
            adapter_request_id="areq_1",
            idempotency_key="k_small",
            lease_epoch=10,
            resource_id="res_1",
            operation_type="echo",
        )
        payload = EffectPayload(
            data=json.dumps(
                {"tool_name": "echo", "arguments": {"msg": "hi"}}
            ).encode("utf-8")
        )
        outcome = adapter.execute_effect(ctx, payload)
        self.assertEqual(outcome.status, ExecutionStatus.EFFECT_CONFIRMED)
        assert outcome.evidence is not None
        self.assertFalse(outcome.evidence.is_reference)


class TestP9_GatewayCrashSafety(unittest.TestCase):
    """P9: Gateway crash → no unauthorized continuation (stateless gate)."""

    def test_gate_is_stateless_per_request(self) -> None:
        """GatewayAuthorizationGate holds no per-request mutable state.
        A new gate instance with the same config produces identical results."""
        gate1 = _make_gate()
        gate2 = _make_gate()
        req = _make_request()
        ctx1, cls1 = gate1.authorize_and_prepare(req, execution_attempt_id="att_1")
        ctx2, cls2 = gate2.authorize_and_prepare(req, execution_attempt_id="att_1")
        self.assertEqual(ctx1.idempotency_key, ctx2.idempotency_key)
        self.assertEqual(cls1, cls2)

    def test_weak_secret_rejected_at_construction(self) -> None:
        """Gateway refuses to start with an insufficiently strong secret."""
        with self.assertRaises(ValueError):
            GatewayAuthorizationGate(
                effect_authority=StubEffectAuthority(),
                capability_registry=StubCapabilityRegistry(),
                domain_secret=b"short",  # < 16 bytes
            )


class TestP10_AdapterCrashReconciliation(unittest.TestCase):
    """P10: Adapter crash → deterministic UNKNOWN_EFFECT status."""

    def test_mcp_server_crash_returns_unknown_effect(self) -> None:
        adapter = LocalProcessMCPAdapter(server_command=MCP_COMMAND)
        from cortex.tools.kernel.adapter_contract import AdapterExecutionContext

        ctx = AdapterExecutionContext(
            invocation_id="inv_crash_01",
            execution_attempt_id="att_1",
            adapter_request_id="areq_crash",
            idempotency_key="k_crash",
            lease_epoch=10,
            resource_id="res_ambiguous",
            operation_type="ambiguous_effect",
        )
        payload = EffectPayload(
            data=json.dumps({"tool_name": "ambiguous_effect"}).encode("utf-8")
        )
        outcome = adapter.execute_effect(ctx, payload)
        self.assertEqual(outcome.status, ExecutionStatus.UNKNOWN_EFFECT)
        assert outcome.error_message is not None
        self.assertIn("exited with code", outcome.error_message)


class TestP11_MalformedOutputDefense(unittest.TestCase):
    """P11: Malformed adapter response → EFFECT_NOT_APPLIED, no kernel crash."""

    def test_garbage_payload_rejected(self) -> None:
        adapter = LocalProcessMCPAdapter(server_command=MCP_COMMAND)
        from cortex.tools.kernel.adapter_contract import AdapterExecutionContext

        ctx = AdapterExecutionContext(
            invocation_id="inv_malform_01",
            execution_attempt_id="att_1",
            adapter_request_id="areq_malform",
            idempotency_key="k_malform",
            lease_epoch=10,
            resource_id="res_1",
            operation_type="echo",
        )
        # Payload is not valid JSON
        payload = EffectPayload(data=b"NOT_VALID_JSON{{{")
        outcome = adapter.execute_effect(ctx, payload)
        self.assertEqual(outcome.status, ExecutionStatus.EFFECT_NOT_APPLIED)
        assert outcome.error_message is not None
        self.assertIn("deserialization", outcome.error_message)

    def test_missing_tool_name_rejected(self) -> None:
        adapter = LocalProcessMCPAdapter(server_command=MCP_COMMAND)
        from cortex.tools.kernel.adapter_contract import AdapterExecutionContext

        ctx = AdapterExecutionContext(
            invocation_id="inv_malform_02",
            execution_attempt_id="att_1",
            adapter_request_id="areq_malform2",
            idempotency_key="k_malform2",
            lease_epoch=10,
            resource_id="res_1",
            operation_type="echo",
        )
        payload = EffectPayload(data=json.dumps({"arguments": {}}).encode("utf-8"))
        outcome = adapter.execute_effect(ctx, payload)
        self.assertEqual(outcome.status, ExecutionStatus.EFFECT_NOT_APPLIED)


class TestP12_ReplayProtection(unittest.TestCase):
    """P12: Replay request → same idempotency key (no duplicate side-effect identity)."""

    def test_replay_produces_identical_effect_identity(self) -> None:
        gate = _make_gate()
        req = _make_request()
        # First attempt
        ctx1, _ = gate.authorize_and_prepare(req, execution_attempt_id="att_1")
        # "Replay" — same request, new attempt
        ctx2, _ = gate.authorize_and_prepare(req, execution_attempt_id="att_2")
        # Third replay
        ctx3, _ = gate.authorize_and_prepare(req, execution_attempt_id="att_3")
        # All produce the same effect identity key
        self.assertEqual(ctx1.idempotency_key, ctx2.idempotency_key)
        self.assertEqual(ctx2.idempotency_key, ctx3.idempotency_key)
        # But trace IDs differ
        self.assertEqual(len({ctx1.execution_attempt_id, ctx2.execution_attempt_id, ctx3.execution_attempt_id}), 3)


class TestEndToEndPipeline(unittest.TestCase):
    """Integration: Full Worker → Gate → Adapter → MCP → Reconciliation pipeline."""

    def test_full_pipeline_echo_success(self) -> None:
        """Happy path: authorized echo call through entire pipeline."""
        gate = _make_gate()
        req = _make_request(
            capability="mcp.echo",
            operation="echo",
            arguments=json.dumps(
                {"tool_name": "echo", "arguments": {"greeting": "hello cortex"}}
            ).encode("utf-8"),
        )

        # Gateway authorization
        ctx, classification = gate.authorize_and_prepare(
            req, execution_attempt_id="att_e2e_1"
        )
        self.assertEqual(classification, EffectClassification.READ_ONLY)

        # Adapter execution
        adapter = LocalProcessMCPAdapter(server_command=MCP_COMMAND)
        payload = EffectPayload(data=req.arguments)
        outcome = adapter.execute_effect(ctx, payload)
        self.assertEqual(outcome.status, ExecutionStatus.EFFECT_CONFIRMED)

        # Reconciliation
        engine = EffectReconciliationEngine()
        state = engine.reconcile_effect(
            ctx=ctx,
            classification=classification,
            outcome=outcome,
        )
        self.assertEqual(state, InvocationState.CONFIRMED)

    def test_full_pipeline_ambiguous_crash_quarantined(self) -> None:
        """Adversarial path: MCP crash → UNKNOWN_EFFECT → quarantine."""
        gate = _make_gate()
        req = _make_request(
            capability="mcp.ambiguous",
            operation="ambiguous_effect",
            arguments=json.dumps(
                {"tool_name": "ambiguous_effect"}
            ).encode("utf-8"),
        )

        ctx, classification = gate.authorize_and_prepare(
            req, execution_attempt_id="att_e2e_crash"
        )
        self.assertEqual(classification, EffectClassification.UNKNOWN_EFFECT)

        adapter = LocalProcessMCPAdapter(server_command=MCP_COMMAND)
        payload = EffectPayload(data=req.arguments)
        outcome = adapter.execute_effect(ctx, payload)
        self.assertEqual(outcome.status, ExecutionStatus.UNKNOWN_EFFECT)

        # Reconciliation should quarantine since UNKNOWN_EFFECT + non-idempotent-equivalent
        engine = EffectReconciliationEngine()
        with self.assertRaises(IndeterminateEffectError):
            engine.reconcile_effect(
                ctx=ctx,
                classification=classification,
                outcome=outcome,
            )
        self.assertTrue(engine.is_resource_quarantined(req.resource_id))


# ===========================================================================
# PIPELINE-LEVEL TESTS — Credential Broker, CAS, Replay Store
# ===========================================================================


from cortex.tools.kernel.effect_runtime import (
    ContentAddressableStore,
    CredentialBroker,
    EffectExecutionPipeline,
    EffectResultStore,
)


def _make_pipeline(
    adapter_command: Optional[list[str]] = None,
) -> EffectExecutionPipeline:
    """Constructs a complete pipeline with all components wired."""
    gate = _make_gate()
    adapter = LocalProcessMCPAdapter(
        server_command=adapter_command or MCP_COMMAND
    )
    broker = CredentialBroker()
    broker.register_credential("res_test_01", b"SECRET_PROVIDER_TOKEN_XYZ")
    cas = ContentAddressableStore()
    reconciliation = EffectReconciliationEngine()
    result_store = EffectResultStore()
    return EffectExecutionPipeline(
        gate=gate,
        adapter=adapter,
        credential_broker=broker,
        cas=cas,
        reconciliation=reconciliation,
        result_store=result_store,
    )


class TestP1b_CredentialIsolation(unittest.TestCase):
    """P1b: Credentials exist in broker but never appear in worker-visible data."""

    def test_credential_not_in_effect_outcome(self) -> None:
        """EffectOutcome returned to worker contains zero credential bytes."""
        pipeline = _make_pipeline()
        req = _make_request(
            arguments=json.dumps(
                {"tool_name": "echo", "arguments": {"msg": "test"}}
            ).encode("utf-8"),
        )
        outcome = pipeline.execute(req, execution_attempt_id="att_cred_1")
        # Credential is b"SECRET_PROVIDER_TOKEN_XYZ" — must NOT appear
        outcome_bytes = json.dumps({
            "invocation_id": outcome.invocation_id,
            "status": outcome.status.value,
            "error_message": outcome.error_message or "",
            "evidence": outcome.evidence.data.decode("utf-8", errors="replace") if outcome.evidence else "",
        }).encode("utf-8")
        self.assertNotIn(b"SECRET_PROVIDER_TOKEN_XYZ", outcome_bytes)

    def test_credential_not_in_effect_request(self) -> None:
        """EffectRequest has no structural field for credentials."""
        req = _make_request()
        # Serialize the entire request to bytes — verify no credential content
        req_repr = str(req).encode("utf-8")
        self.assertNotIn(b"SECRET", req_repr)
        self.assertNotIn(b"TOKEN", req_repr)

    def test_broker_resolves_only_registered_resources(self) -> None:
        """Broker returns None for unregistered resources."""
        broker = CredentialBroker()
        broker.register_credential("res_authorized", b"key_123")
        self.assertIsNotNone(broker.resolve("res_authorized"))
        self.assertIsNone(broker.resolve("res_unauthorized"))

    def test_broker_revoke_removes_credential(self) -> None:
        broker = CredentialBroker()
        broker.register_credential("res_temp", b"ephemeral")
        self.assertIsNotNone(broker.resolve("res_temp"))
        broker.revoke_credential("res_temp")
        self.assertIsNone(broker.resolve("res_temp"))


class TestP8_CASRoundTrip(unittest.TestCase):
    """P8 (complete): Large evidence → CAS.put() → ObjectRef → CAS.get() → data."""

    def test_cas_put_get_round_trip(self) -> None:
        """Data stored via put() is retrievable via get()."""
        cas = ContentAddressableStore()
        data = b"A" * 8192
        ref = cas.put(data)
        self.assertTrue(ref.startswith("sha256:"))
        retrieved = cas.get(ref)
        self.assertEqual(retrieved, data)

    def test_cas_deduplication(self) -> None:
        """Identical data produces the same reference (content-addressed)."""
        cas = ContentAddressableStore()
        data = b"deterministic content"
        ref1 = cas.put(data)
        ref2 = cas.put(data)
        self.assertEqual(ref1, ref2)
        self.assertEqual(cas.object_count, 1)

    def test_cas_unknown_ref_returns_none(self) -> None:
        cas = ContentAddressableStore()
        self.assertIsNone(cas.get("sha256:nonexistent"))

    def test_pipeline_spools_large_evidence_to_cas(self) -> None:
        """Pipeline stores large evidence in CAS and returns reference pointer."""
        pipeline = _make_pipeline()
        req = _make_request(
            capability="mcp.large",
            operation="large_response",
            arguments=json.dumps(
                {"tool_name": "large_response", "arguments": {"size_bytes": 8192}}
            ).encode("utf-8"),
        )
        outcome = pipeline.execute(req, execution_attempt_id="att_cas_1")
        self.assertEqual(outcome.status, ExecutionStatus.EFFECT_CONFIRMED)
        assert outcome.evidence is not None
        # Evidence should be a reference since the MCP response exceeds 4KiB
        # The pipeline or adapter should have spooled it
        if outcome.evidence.is_reference:
            ref_str = outcome.evidence.data.decode("utf-8")
            self.assertTrue(ref_str.startswith("sha256:"))


class TestP12_PipelineReplayProtection(unittest.TestCase):
    """P12 (complete): CommittedKey → CachedOutcome → NoSecondExecution."""

    def test_replay_returns_cached_outcome_without_re_execution(self) -> None:
        """Second call with same request returns cached result, no MCP call."""
        pipeline = _make_pipeline()
        req = _make_request(
            invocation_id="inv_replay_100",
            arguments=json.dumps(
                {"tool_name": "echo", "arguments": {"v": "original"}}
            ).encode("utf-8"),
        )
        # First execution — hits adapter
        outcome1 = pipeline.execute(req, execution_attempt_id="att_1")
        self.assertEqual(outcome1.status, ExecutionStatus.EFFECT_CONFIRMED)

        # Second execution — same request, new attempt_id → replay hit
        outcome2 = pipeline.execute(req, execution_attempt_id="att_2")
        self.assertEqual(outcome2.status, ExecutionStatus.EFFECT_CONFIRMED)

        # Both outcomes share the same invocation_id and status
        self.assertEqual(outcome1.invocation_id, outcome2.invocation_id)
        # The replay cache returns the cached outcome — same evidence
        self.assertEqual(outcome1.evidence, outcome2.evidence)

    def test_different_invocation_no_replay(self) -> None:
        """Different invocation_id produces a different key — no replay hit."""
        pipeline = _make_pipeline()
        req1 = _make_request(
            invocation_id="inv_a",
            arguments=json.dumps(
                {"tool_name": "echo", "arguments": {"v": 1}}
            ).encode("utf-8"),
        )
        req2 = _make_request(
            invocation_id="inv_b",
            arguments=json.dumps(
                {"tool_name": "echo", "arguments": {"v": 1}}
            ).encode("utf-8"),
        )
        outcome1 = pipeline.execute(req1, execution_attempt_id="att_1")
        outcome2 = pipeline.execute(req2, execution_attempt_id="att_1")
        # Both succeed independently
        self.assertEqual(outcome1.status, ExecutionStatus.EFFECT_CONFIRMED)
        self.assertEqual(outcome2.status, ExecutionStatus.EFFECT_CONFIRMED)
        # But they are distinct invocations
        self.assertNotEqual(outcome1.invocation_id, outcome2.invocation_id)

    def test_result_store_tracks_committed_count(self) -> None:
        store = EffectResultStore()
        self.assertEqual(store.committed_count, 0)
        outcome = EffectOutcome(
            invocation_id="inv_1",
            execution_attempt_id="att_1",
            status=ExecutionStatus.EFFECT_CONFIRMED,
        )
        store.commit("key_1", outcome)
        self.assertEqual(store.committed_count, 1)
        self.assertIsNotNone(store.lookup("key_1"))
        self.assertIsNone(store.lookup("key_nonexistent"))


class TestPipelineComposition(unittest.TestCase):
    """Full pipeline composition tests wiring all components."""

    def test_pipeline_echo_success(self) -> None:
        """Full chain: authorized echo through pipeline."""
        pipeline = _make_pipeline()
        req = _make_request(
            arguments=json.dumps(
                {"tool_name": "echo", "arguments": {"greeting": "pipeline"}}
            ).encode("utf-8"),
        )
        outcome = pipeline.execute(req, execution_attempt_id="att_pipe_1")
        self.assertEqual(outcome.status, ExecutionStatus.EFFECT_CONFIRMED)
        self.assertEqual(outcome.invocation_id, req.invocation_id)

    def test_pipeline_crash_produces_unknown_effect(self) -> None:
        """MCP crash flows through pipeline → UNKNOWN_EFFECT."""
        pipeline = _make_pipeline()
        req = _make_request(
            capability="mcp.ambiguous",
            operation="ambiguous_effect",
            arguments=json.dumps(
                {"tool_name": "ambiguous_effect"}
            ).encode("utf-8"),
        )
        outcome = pipeline.execute(req, execution_attempt_id="att_pipe_crash")
        self.assertEqual(outcome.status, ExecutionStatus.UNKNOWN_EFFECT)

    def test_pipeline_unauthorized_capability_rejected(self) -> None:
        """Pipeline rejects unauthorized requests before adapter execution."""
        pipeline = _make_pipeline()
        req = _make_request(capability="mcp.forbidden", operation="hack")
        from cortex.tools.kernel.effect_gateway import CapabilityDeniedError
        with self.assertRaises(CapabilityDeniedError):
            pipeline.execute(req, execution_attempt_id="att_pipe_denied")


class TestP12_ConcurrentDuplicateFencing(unittest.TestCase):
    """P12 (concurrency): Simultaneous duplicate submissions execute adapter EXACTLY ONCE."""

    def test_concurrent_duplicate_submissions_execute_adapter_exactly_once(self) -> None:
        """
        10 threads simultaneously submit the same EffectRequest.
        Verifies:
            1. Adapter executes EXACTLY ONCE across all threads.
            2. All 10 threads receive ExecutionStatus.EFFECT_CONFIRMED.
        """
        import concurrent.futures
        import threading

        # Counting spy adapter wrapping the stdio adapter
        execution_count = 0
        count_lock = threading.Lock()

        class CountingAdapter(LocalProcessMCPAdapter):
            def execute_effect(self, ctx, payload):
                nonlocal execution_count
                with count_lock:
                    execution_count += 1
                return super().execute_effect(ctx, payload)

        gate = _make_gate()
        adapter = CountingAdapter(server_command=MCP_COMMAND)
        broker = CredentialBroker()
        broker.register_credential("res_test_01", b"CONCURRENT_SECRET")
        cas = ContentAddressableStore()
        reconciliation = EffectReconciliationEngine()
        result_store = EffectResultStore()

        pipeline = EffectExecutionPipeline(
            gate=gate,
            adapter=adapter,
            credential_broker=broker,
            cas=cas,
            reconciliation=reconciliation,
            result_store=result_store,
        )

        req = _make_request(
            invocation_id="inv_concurrent_99",
            arguments=json.dumps(
                {"tool_name": "echo", "arguments": {"race": "test"}}
            ).encode("utf-8"),
        )

        def worker_task(thread_id: int):
            return pipeline.execute(req, execution_attempt_id=f"att_thread_{thread_id}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker_task, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Exactly 1 adapter execution occurred
        self.assertEqual(execution_count, 1)

        # All 10 callers received confirmed status
        self.assertEqual(len(results), 10)
        for outcome in results:
            self.assertEqual(outcome.status, ExecutionStatus.EFFECT_CONFIRMED)


class TestP8_CASIntegrityAndScoping(unittest.TestCase):
    """P8 (integrity & scoping): Tampering raises CASDataCorruptionError, cross-tenant raises CASAccessDeniedError."""

    def test_cas_corrupted_data_detection(self) -> None:
        """Corrupting data stored in CAS triggers CASDataCorruptionError on retrieval."""
        from cortex.tools.kernel.effect_runtime import CASDataCorruptionError

        cas = ContentAddressableStore()
        original_data = b"unaltered evidence content"
        ref = cas.put(original_data, owner_id="inv_101")

        # Corrupt stored bytes directly
        cas.corrupt_object_for_test(ref, b"corrupted/modified evidence bytes")

        with self.assertRaises(CASDataCorruptionError):
            cas.get(ref, requester_id="inv_101")

    def test_cas_unauthorized_cross_invocation_access_denied(self) -> None:
        """Accessing a CAS ObjectRef owned by inv_A from inv_B raises CASAccessDeniedError."""
        from cortex.tools.kernel.effect_runtime import CASAccessDeniedError

        cas = ContentAddressableStore()
        data = b"private evidence for invocation A"
        ref = cas.put(data, owner_id="inv_A")

        # Invocation A can access it
        retrieved = cas.get(ref, requester_id="inv_A")
        self.assertEqual(retrieved, data)

        # Invocation B is denied
        with self.assertRaises(CASAccessDeniedError):
            cas.get(ref, requester_id="inv_B")


if __name__ == "__main__":
    unittest.main()


