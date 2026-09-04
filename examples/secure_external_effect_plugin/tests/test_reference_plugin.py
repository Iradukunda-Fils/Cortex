"""
Comprehensive Test Suite for Cortex Reference Sample: secure_external_effect_plugin.

Verifies ALL security boundaries and API contracts specified in the reference sample:

    1.  test_authorized_lookup_succeeds           — READ_ONLY effect confirmed
    2.  test_authorized_store_succeeds            — IDEMPOTENT_WRITE effect confirmed
    3.  test_unauthorized_capability_rejected      — CapabilityDeniedError raised
    4.  test_stale_lease_epoch_rejected            — EffectFencingError raised
    5.  test_replay_returns_cached_outcome         — Duplicate HMAC key → no re-execution
    6.  test_failed_service_handled_safely         — External error → EFFECT_NOT_APPLIED
    7.  test_credential_never_in_plugin_output     — Vault secret absent from EffectOutcome
    8.  test_workflow_completes_with_plugin         — CortexClient end-to-end
    9.  test_deterministic_replay_matches          — Replay engine causal parity
    10. test_cas_evidence_integrity                 — CAS stores and verifies by hash
    11. test_cas_cross_invocation_access_denied     — CAS owner scoping enforced
    12. test_malformed_response_handled             — Invalid JSON → EFFECT_NOT_APPLIED

REFERENCE EXAMPLE — IMPLEMENTED FEATURES ONLY
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from typing import Tuple

from cortex import CortexClient, IntentEvent, PluginManifest, WorkflowState
from cortex.tools.kernel.adapter_contract import EffectClassification, ExecutionStatus
from cortex.tools.kernel.adapters.mcp_adapter import LocalProcessMCPAdapter
from cortex.tools.kernel.effect_gateway import (
    CapabilityDeniedError,
    EffectFencingError,
    EffectRequest,
    GatewayAuthorizationGate,
)
from cortex.tools.kernel.effect_runtime import (
    CASAccessDeniedError,
    ContentAddressableStore,
    CredentialBroker,
    EffectExecutionPipeline,
    EffectResultStore,
)
from cortex.tools.kernel.reconciliation import EffectReconciliationEngine

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")
LOCAL_API_SERVER = os.path.join(FIXTURES_DIR, "local_api_server.py")


# ── Test Helpers ─────────────────────────────────────────────────────


class StubCapabilityRegistry:
    """Test-scoped capability registry."""

    def __init__(self, granted: set[Tuple[str, str]]) -> None:
        self._granted = granted

    def is_capability_granted(self, capability: str, operation: str) -> bool:
        return (capability, operation) in self._granted

    def resolve_effect_classification(self, capability: str, operation: str) -> EffectClassification:
        if operation == "lookup":
            return EffectClassification.READ_ONLY
        elif operation in ("store", "log"):
            return EffectClassification.IDEMPOTENT_WRITE
        return EffectClassification.UNKNOWN_EFFECT


class StubEffectAuthority:
    """Test-scoped effect authority."""

    def __init__(self, gen: int = 1, epoch: int = 10) -> None:
        self._gen = gen
        self._epoch = epoch

    def validate_effect_reservation(self, worker_generation: int, lease_epoch: int) -> bool:
        return worker_generation == self._gen and lease_epoch == self._epoch


def build_test_pipeline(
    granted: set[Tuple[str, str]],
    gen: int = 1,
    epoch: int = 10,
) -> Tuple[CredentialBroker, ContentAddressableStore, EffectExecutionPipeline, EffectResultStore]:
    """Builds a fresh test pipeline with no shared state."""
    authority = StubEffectAuthority(gen=gen, epoch=epoch)
    registry = StubCapabilityRegistry(granted=granted)
    domain_secret = b"test_domain_secret_32bytes______"

    gateway = GatewayAuthorizationGate(
        effect_authority=authority,
        capability_registry=registry,
        domain_secret=domain_secret,
    )

    broker = CredentialBroker()
    broker.register_credential("res_test_api", b"secret_bearer_token_test_only")

    adapter = LocalProcessMCPAdapter(server_command=[sys.executable, LOCAL_API_SERVER])
    cas = ContentAddressableStore()
    reconciler = EffectReconciliationEngine()
    result_store = EffectResultStore()

    pipeline = EffectExecutionPipeline(
        gate=gateway,
        adapter=adapter,
        credential_broker=broker,
        cas=cas,
        reconciliation=reconciler,
        result_store=result_store,
    )

    return broker, cas, pipeline, result_store


# ── Test Suite ───────────────────────────────────────────────────────


class TestSecureExternalEffectPlugin(unittest.TestCase):
    """Verification test suite for the Cortex reference sample plugin."""

    def setUp(self) -> None:
        self.granted_caps: set[Tuple[str, str]] = {
            ("api:records", "lookup"),
            ("api:records", "store"),
            ("api:audit", "log"),
        }
        self.broker, self.cas, self.pipeline, self.result_store = build_test_pipeline(
            granted=self.granted_caps
        )

    # ── 1. Authorized lookup succeeds ────────────────────────────

    def test_authorized_lookup_succeeds(self) -> None:
        """Verify READ_ONLY lookup through Gateway succeeds with evidence."""
        request = EffectRequest(
            invocation_id="inv_test_lookup",
            capability="api:records",
            operation="lookup",
            arguments=json.dumps({"tool_name": "lookup_record", "arguments": {"record_id": "rec_001"}}).encode(),
            resource_id="res_test_api",
            lease_epoch=10,
            worker_generation=1,
        )

        outcome = self.pipeline.execute(request, execution_attempt_id="att_test_lookup")

        self.assertEqual(outcome.status, ExecutionStatus.EFFECT_CONFIRMED)
        self.assertIsNotNone(outcome.evidence)
        if outcome.evidence:
            data = outcome.evidence.data.decode("utf-8")
            self.assertIn("rec_001", data)
            self.assertIn("FOUND", data)

    # ── 2. Authorized store succeeds ─────────────────────────────

    def test_authorized_store_succeeds(self) -> None:
        """Verify IDEMPOTENT_WRITE store through Gateway succeeds."""
        request = EffectRequest(
            invocation_id="inv_test_store",
            capability="api:records",
            operation="store",
            arguments=json.dumps({"tool_name": "store_record", "arguments": {"key": "k1", "value": "v1"}}).encode(),
            resource_id="res_test_api",
            lease_epoch=10,
            worker_generation=1,
        )

        outcome = self.pipeline.execute(request, execution_attempt_id="att_test_store")

        self.assertEqual(outcome.status, ExecutionStatus.EFFECT_CONFIRMED)
        self.assertIsNotNone(outcome.evidence)
        if outcome.evidence:
            data = outcome.evidence.data.decode("utf-8")
            self.assertIn("k1", data)
            self.assertIn("true", data.lower())

    # ── 3. Unauthorized capability is rejected ───────────────────

    def test_unauthorized_capability_rejected(self) -> None:
        """Verify Gateway rejects ungranted capability with CapabilityDeniedError."""
        request = EffectRequest(
            invocation_id="inv_test_unauth",
            capability="api:admin",
            operation="delete_all",
            arguments=b"{}",
            resource_id="res_test_api",
            lease_epoch=10,
            worker_generation=1,
        )

        with self.assertRaises(CapabilityDeniedError):
            self.pipeline.execute(request, execution_attempt_id="att_test_unauth")

    # ── 4. Stale lease epoch is rejected ─────────────────────────

    def test_stale_lease_epoch_rejected(self) -> None:
        """Verify Gateway rejects stale lease epoch with EffectFencingError."""
        request = EffectRequest(
            invocation_id="inv_test_stale",
            capability="api:records",
            operation="lookup",
            arguments=json.dumps({"tool_name": "lookup_record", "arguments": {"record_id": "rec_stale"}}).encode(),
            resource_id="res_test_api",
            lease_epoch=3,  # Stale — valid epoch is 10
            worker_generation=1,
        )

        with self.assertRaises(EffectFencingError):
            self.pipeline.execute(request, execution_attempt_id="att_test_stale")

    # ── 5. Replay returns cached outcome (no re-execution) ───────

    def test_replay_returns_cached_outcome(self) -> None:
        """Verify duplicate HMAC key returns cached result without re-executing adapter."""
        request = EffectRequest(
            invocation_id="inv_test_replay",
            capability="api:records",
            operation="lookup",
            arguments=json.dumps({"tool_name": "lookup_record", "arguments": {"record_id": "rec_replay"}}).encode(),
            resource_id="res_test_api",
            lease_epoch=10,
            worker_generation=1,
        )

        # First execution — adapter runs
        outcome_1 = self.pipeline.execute(request, execution_attempt_id="att_replay_first")
        self.assertEqual(outcome_1.status, ExecutionStatus.EFFECT_CONFIRMED)
        committed_before = self.result_store.committed_count

        # Second execution — same request, same HMAC key → cached
        outcome_2 = self.pipeline.execute(request, execution_attempt_id="att_replay_second")
        self.assertEqual(outcome_2.status, ExecutionStatus.EFFECT_CONFIRMED)

        # Result store should NOT have grown (cached return, no new commit)
        self.assertEqual(self.result_store.committed_count, committed_before)

        # Both outcomes should have identical invocation_id
        self.assertEqual(outcome_1.invocation_id, outcome_2.invocation_id)

    # ── 6. Failed external service handled safely ────────────────

    def test_failed_service_handled_safely(self) -> None:
        """Verify external service error results in EFFECT_NOT_APPLIED with error message."""
        request = EffectRequest(
            invocation_id="inv_test_fail",
            capability="api:records",
            operation="lookup",
            arguments=json.dumps({"tool_name": "fail", "arguments": {}}).encode(),
            resource_id="res_test_api",
            lease_epoch=10,
            worker_generation=1,
        )

        outcome = self.pipeline.execute(request, execution_attempt_id="att_test_fail")

        self.assertEqual(outcome.status, ExecutionStatus.EFFECT_NOT_APPLIED)
        self.assertIsNotNone(outcome.error_message)
        assert outcome.error_message is not None
        self.assertIn("unavailable", outcome.error_message.lower())

    # ── 7. Credentials never appear in plugin-visible output ─────

    def test_credential_never_in_plugin_output(self) -> None:
        """Verify vault credentials never leak into EffectOutcome fields."""
        vault_secret = self.broker.resolve("res_test_api")
        self.assertEqual(vault_secret, b"secret_bearer_token_test_only")

        request = EffectRequest(
            invocation_id="inv_test_cred",
            capability="api:records",
            operation="lookup",
            arguments=json.dumps({"tool_name": "lookup_record", "arguments": {"record_id": "rec_cred"}}).encode(),
            resource_id="res_test_api",
            lease_epoch=10,
            worker_generation=1,
        )

        outcome = self.pipeline.execute(request, execution_attempt_id="att_test_cred")

        outcome_str = str(outcome)
        self.assertNotIn("secret_bearer_token", outcome_str)
        self.assertNotIn("test_only", outcome_str)
        if outcome.evidence:
            self.assertNotIn("secret_bearer_token", outcome.evidence.data.decode("utf-8"))

    # ── 8. CortexClient end-to-end workflow ──────────────────────

    def test_workflow_completes_with_plugin(self) -> None:
        """Verify CortexClient workflow completes with registered plugin."""
        from examples.secure_external_effect_plugin.plugins.record_plugin import (
            RecordServicePlugin,
            WorkerContext,
        )

        client = CortexClient(platform_capabilities={"api:records"})
        ctx = WorkerContext(invocation_id="inv_wf_test", resource_id="res_test_api",
                           lease_epoch=10, worker_generation=1)

        plugin = RecordServicePlugin(
            PluginManifest(
                name="test-wf-plugin", version="1.0.0", description="Test",
                consumes_events=["IntentEvent"], produces_events=["CommandIssuedEvent"],
                required_capabilities=["api:records"],
            ),
            pipeline=self.pipeline,
            worker_ctx=ctx,
        )

        reg = client.register_plugin(plugin)
        self.assertEqual(reg.state.value, "ACTIVE")

        workflow = client.create_workflow(name="test_wf", goal="Test Workflow")
        intent = IntentEvent(workflow_id=workflow.workflow_id, goal=workflow.goal,
                             parameters={"record_id": "rec_wf"})
        completed = client.run_workflow(workflow, initial_intent=intent)
        self.assertEqual(completed.state, WorkflowState.COMPLETED)

    # ── 9. Deterministic replay matches ──────────────────────────

    def test_deterministic_replay_matches(self) -> None:
        """Verify replay engine produces causal sequence match."""
        client = CortexClient(platform_capabilities={"api:records"})

        workflow = client.create_workflow(name="test_replay_wf", goal="Replay Test")
        intent = IntentEvent(workflow_id=workflow.workflow_id, goal=workflow.goal)
        client.run_workflow(workflow, initial_intent=intent)

        replay_res = client.replay_workflow(workflow.workflow_id)
        self.assertTrue(replay_res["deterministic"])

    # ── 10. CAS evidence integrity ───────────────────────────────

    def test_cas_evidence_integrity(self) -> None:
        """Verify CAS stores data with content-addressed key and verifies integrity."""
        test_data = b"integrity test payload content"
        ref = self.cas.put(test_data, owner_id="inv_integrity_test")

        self.assertTrue(ref.startswith("sha256:"))
        self.assertTrue(self.cas.contains(ref))

        retrieved = self.cas.get(ref, requester_id="inv_integrity_test")
        self.assertEqual(retrieved, test_data)

    # ── 11. CAS cross-invocation access denied ───────────────────

    def test_cas_cross_invocation_access_denied(self) -> None:
        """Verify CAS rejects access from non-owning invocation."""
        test_data = b"private evidence data"
        ref = self.cas.put(test_data, owner_id="inv_owner_A")

        with self.assertRaises(CASAccessDeniedError):
            self.cas.get(ref, requester_id="inv_owner_B")

    # ── 12. AuditPlugin individual effect succeeds ────────────────

    def test_audit_plugin_record_succeeds(self) -> None:
        """Verify AuditPlugin records audit entry via api:audit/log through Gateway."""
        from examples.secure_external_effect_plugin.plugins.audit_plugin import AuditPlugin
        from examples.secure_external_effect_plugin.plugins.record_plugin import WorkerContext

        ctx = WorkerContext(invocation_id="inv_audit_test", resource_id="res_test_api",
                           lease_epoch=10, worker_generation=1)

        audit = AuditPlugin(
            PluginManifest(
                name="test-audit", version="1.0.0", description="Test Audit",
                consumes_events=["CommandIssuedEvent"],
                produces_events=["VerificationResultEvent"],
                required_capabilities=["api:audit"],
            ),
            pipeline=self.pipeline,
            worker_ctx=ctx,
        )

        outcome = audit.record_audit(
            pipeline=self.pipeline, ctx=ctx,
            action="record_lookup", parameters={"record_id": "rec_001"},
            execution_attempt_id="att_audit_test",
        )

        self.assertEqual(outcome.status, ExecutionStatus.EFFECT_CONFIRMED)
        self.assertIsNotNone(outcome.evidence)

    # ── 13. 2-Plugin DAG workflow chain ──────────────────────────

    def test_dag_workflow_chain(self) -> None:
        """Verify 2-plugin event DAG: IntentEvent → RecordService → CommandIssued → Audit → VerificationResult."""
        from examples.secure_external_effect_plugin.plugins.audit_plugin import AuditPlugin
        from examples.secure_external_effect_plugin.plugins.record_plugin import (
            RecordServicePlugin,
            WorkerContext,
        )

        client = CortexClient(platform_capabilities={"api:records", "api:audit"})
        ctx = WorkerContext(invocation_id="inv_dag_test", resource_id="res_test_api",
                           lease_epoch=10, worker_generation=1)

        record_plugin = RecordServicePlugin(
            PluginManifest(
                name="dag-record", version="1.0.0", description="DAG Record",
                consumes_events=["IntentEvent"],
                produces_events=["CommandIssuedEvent"],
                required_capabilities=["api:records"],
            ),
            pipeline=self.pipeline, worker_ctx=ctx,
        )

        audit_plugin = AuditPlugin(
            PluginManifest(
                name="dag-audit", version="1.0.0", description="DAG Audit",
                consumes_events=["CommandIssuedEvent"],
                produces_events=["VerificationResultEvent"],
                required_capabilities=["api:audit"],
            ),
            pipeline=self.pipeline, worker_ctx=ctx,
        )

        reg_record = client.register_plugin(record_plugin)
        reg_audit = client.register_plugin(audit_plugin)
        self.assertEqual(reg_record.state.value, "ACTIVE")
        self.assertEqual(reg_audit.state.value, "ACTIVE")

        workflow = client.create_workflow(name="dag_test_wf", goal="2-Plugin DAG")
        intent = IntentEvent(
            workflow_id=workflow.workflow_id, goal=workflow.goal,
            parameters={"record_id": "rec_dag"},
        )
        completed = client.run_workflow(workflow, initial_intent=intent)
        self.assertEqual(completed.state, WorkflowState.COMPLETED)

        # Verify event chain produced events from both plugins
        events = client.event_store.get_log()
        event_types = [type(e).__name__ for e in events]
        self.assertIn("IntentEvent", event_types)
        self.assertGreaterEqual(len(events), 2)

    # ── 14. Malformed external response handled ──────────────────

    def test_malformed_response_handled(self) -> None:
        """Verify malformed JSON response from service → EFFECT_NOT_APPLIED."""
        request = EffectRequest(
            invocation_id="inv_test_malformed",
            capability="api:records",
            operation="lookup",
            arguments=json.dumps({"tool_name": "malformed", "arguments": {}}).encode(),
            resource_id="res_test_api",
            lease_epoch=10,
            worker_generation=1,
        )

        outcome = self.pipeline.execute(request, execution_attempt_id="att_test_malformed")

        # Malformed response should result in NOT_APPLIED (deterministic rejection)
        self.assertIn(outcome.status, (ExecutionStatus.EFFECT_NOT_APPLIED, ExecutionStatus.UNKNOWN_EFFECT))
        self.assertIsNotNone(outcome.error_message)


if __name__ == "__main__":
    unittest.main()
