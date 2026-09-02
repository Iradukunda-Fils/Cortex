"""
Comprehensive Multi-Perspective Test Suite for mcp_secure_effect_app reference project.

Tests:
  1. 1-to-Many Event Fan-Out & Emergent autonomous workflow execution across 5 plugins
  2. Execution graph lineage inspection & root-cause tracing
  3. Deterministic replay engine immutability
  4. Individual plugin unit execution
  5. Notification fan-out alert plugin execution
  6. Content-Addressable Storage (CAS) evidence auto-spooling for >4KiB payloads
  7. Gateway capability grant sandboxing
  8. Worker lease epoch fencing
  9. Credential isolation vault non-leakage
"""

from __future__ import annotations

import unittest
from cortex import CortexClient, IntentEvent, PluginManifest
from cortex.schema.workflow import WorkflowState
from cortex.tools.kernel.adapter_contract import ExecutionStatus
from cortex.tools.kernel.effect_gateway import (
    CapabilityDeniedError,
    EffectFencingError,
    EffectRequest,
)

from ..main import build_cortex_effect_runtime
from ..plugins.analytics_plugin.tasks import AnalyticsPlugin
from ..plugins.audit_plugin.tasks import AuditPlugin
from ..plugins.ingestion_plugin.tasks import ExecutionContext, IngestionPlugin
from ..plugins.mitigation_plugin.tasks import MitigationPlugin
from ..plugins.notification_plugin.tasks import NotificationPlugin


class TestMCPSecureEffectApp(unittest.TestCase):
    """Production readiness test suite for mcp_secure_effect_app."""

    def setUp(self) -> None:
        self.granted_caps = {
            ("mcp:echo", "echo"),
            ("mcp:report", "generate_report"),
            ("mcp:mitigate", "rebalance_resources"),
            ("mcp:notify", "send_alert"),
            ("mcp:audit", "audit_log"),
        }
        self.broker, self.cas, self.pipeline = build_cortex_effect_runtime(
            granted_capabilities=self.granted_caps,
            valid_generation=1,
            valid_epoch=10,
        )

        self.client = CortexClient(platform_capabilities={"mcp:echo", "mcp:report", "mcp:mitigate", "mcp:notify", "mcp:audit"})
        self.ctx = ExecutionContext(
            invocation_id="inv_test_001",
            resource_id="res_external_mcp",
            lease_epoch=10,
            worker_generation=1,
        )

        self.ingest_plugin = IngestionPlugin(
            PluginManifest(
                name="ingestion-plugin",
                version="1.0.0",
                description="Ingestion",
                consumes_events=["IntentEvent"],
                produces_events=["CommandIssuedEvent"],
                required_capabilities=["mcp:echo"],
            ),
            pipeline=self.pipeline,
            exec_ctx=self.ctx,
        )

        self.analytics_plugin = AnalyticsPlugin(
            PluginManifest(
                name="analytics-plugin",
                version="1.0.0",
                description="Analytics",
                consumes_events=["CommandIssuedEvent"],
                produces_events=["DriverTelemetryEvent"],
                required_capabilities=["mcp:report"],
            ),
            pipeline=self.pipeline,
            exec_ctx=self.ctx,
        )

        self.mitigation_plugin = MitigationPlugin(
            PluginManifest(
                name="mitigation-plugin",
                version="1.0.0",
                description="Mitigation",
                consumes_events=["DriverTelemetryEvent"],
                produces_events=["PlanGeneratedEvent"],
                required_capabilities=["mcp:mitigate"],
            ),
            pipeline=self.pipeline,
            exec_ctx=self.ctx,
        )

        self.notification_plugin = NotificationPlugin(
            PluginManifest(
                name="notification-plugin",
                version="1.0.0",
                description="Notification",
                consumes_events=["DriverTelemetryEvent"],
                produces_events=["CommandIssuedEvent"],
                required_capabilities=["mcp:notify"],
            ),
            pipeline=self.pipeline,
            exec_ctx=self.ctx,
        )

        self.audit_plugin = AuditPlugin(
            PluginManifest(
                name="audit-plugin",
                version="1.0.0",
                description="Audit",
                consumes_events=["PlanGeneratedEvent"],
                produces_events=["VerificationResultEvent"],
                required_capabilities=["mcp:audit"],
            ),
            pipeline=self.pipeline,
            exec_ctx=self.ctx,
        )

        self.client.register_plugin(self.ingest_plugin)
        self.client.register_plugin(self.analytics_plugin)
        self.client.register_plugin(self.mitigation_plugin)
        self.client.register_plugin(self.notification_plugin)
        self.client.register_plugin(self.audit_plugin)

    def test_emergent_fanout_workflow(self) -> None:
        workflow = self.client.create_workflow(name="test_fanout_wf", goal="Autonomous Event Fan-Out")
        intent = IntentEvent(
            workflow_id=workflow.workflow_id,
            goal=workflow.goal,
            parameters={"sensor": "S100"},
        )

        completed_wf = self.client.run_workflow(workflow, initial_intent=intent)
        self.assertEqual(completed_wf.state, WorkflowState.COMPLETED)
        # Event chain includes fan-out: IntentEvent -> CommandIssued -> DriverTelemetry -> PlanGenerated (mitigation) + CommandIssued (notify) -> VerificationResult
        self.assertGreaterEqual(len(self.client.event_store.get_log()), 6)

    def test_workflow_graph_lineage_inspection(self) -> None:
        workflow = self.client.create_workflow(name="test_graph_wf", goal="Test Graph Lineage")
        intent = IntentEvent(workflow_id=workflow.workflow_id, goal=workflow.goal)
        self.client.run_workflow(workflow, initial_intent=intent)

        inspection = self.client.inspect_workflow(workflow.workflow_id)
        self.assertGreater(inspection.get("node_count", 0), 0)
        failed_nodes = inspection.get("failed_nodes", [])
        self.assertEqual(len(failed_nodes) if isinstance(failed_nodes, list) else 0, 0)

    def test_deterministic_replay_engine(self) -> None:
        workflow = self.client.create_workflow(name="test_replay_wf", goal="Test Replay Engine")
        intent = IntentEvent(workflow_id=workflow.workflow_id, goal=workflow.goal)
        self.client.run_workflow(workflow, initial_intent=intent)

        replay_res = self.client.replay_workflow(workflow.workflow_id)
        self.assertTrue(replay_res["deterministic"])
        self.assertGreater(replay_res["replayed_count"], 0)

    def test_notification_plugin_succeeds(self) -> None:
        outcome = self.notification_plugin.send_alert(
            pipeline=self.pipeline,
            ctx=self.ctx,
            execution_attempt_id="att_test_notify",
        )

        self.assertEqual(outcome.status, ExecutionStatus.EFFECT_COMMITTED)
        self.assertIsNotNone(outcome.evidence)
        if outcome.evidence:
            self.assertIn("DELIVERED", outcome.evidence.data.decode("utf-8"))

    def test_analytics_plugin_spools_evidence_to_cas(self) -> None:
        outcome = self.analytics_plugin.generate_report(
            pipeline=self.pipeline,
            ctx=self.ctx,
            size_bytes=8192,
            execution_attempt_id="att_test_analytics",
        )

        self.assertEqual(outcome.status, ExecutionStatus.EFFECT_COMMITTED)
        self.assertIsNotNone(outcome.evidence)
        if outcome.evidence:
            self.assertTrue(outcome.evidence.is_reference)
            self.assertIsNotNone(outcome.evidence.content_hash)
            spooled = self.cas.retrieve(
                content_hash=outcome.evidence.content_hash,
                requesting_invocation_id=self.ctx.invocation_id,
            )
            self.assertGreaterEqual(len(spooled), 8192)

    def test_ungranted_capability_is_rejected(self) -> None:
        unauthorized_req = EffectRequest(
            invocation_id=self.ctx.invocation_id,
            capability="mcp:unauthorized",
            operation="restricted_op",
            arguments=b"{}",
            resource_id=self.ctx.resource_id,
            lease_epoch=self.ctx.lease_epoch,
            worker_generation=self.ctx.worker_generation,
        )

        with self.assertRaises(CapabilityDeniedError):
            self.pipeline.execute(unauthorized_req, execution_attempt_id="att_test_unauth")

    def test_stale_lease_epoch_is_rejected(self) -> None:
        stale_req = EffectRequest(
            invocation_id=self.ctx.invocation_id,
            capability="mcp:echo",
            operation="echo",
            arguments=b'{"tool_name": "echo", "arguments": {}}',
            resource_id=self.ctx.resource_id,
            lease_epoch=7,  # Stale (valid = 10)
            worker_generation=self.ctx.worker_generation,
        )

        with self.assertRaises(EffectFencingError):
            self.pipeline.execute(stale_req, execution_attempt_id="att_test_stale")

    def test_credential_isolation_vault(self) -> None:
        vault_secret = self.broker.resolve("res_external_mcp")
        self.assertEqual(vault_secret, b"secret_bearer_token_xyz987")

        outcome = self.ingest_plugin.ingest_payload(
            pipeline=self.pipeline,
            ctx=self.ctx,
            raw_data={"data": "sample"},
            execution_attempt_id="att_test_cred",
        )

        self.assertNotIn("secret_bearer_token", str(outcome))


if __name__ == "__main__":
    unittest.main()
