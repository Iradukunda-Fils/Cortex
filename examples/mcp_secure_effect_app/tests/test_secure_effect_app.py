"""
Integration test suite for mcp_secure_effect_app 3-plugin reference application.
"""

from __future__ import annotations

import unittest
from cortex.tools.kernel.adapter_contract import ExecutionStatus
from cortex.tools.kernel.effect_gateway import (
    CapabilityDeniedError,
    EffectFencingError,
    EffectRequest,
)
from cortex.plugin import PluginManifest

from ..main import build_cortex_effect_runtime
from ..plugins.ingestion_plugin.tasks import ExecutionContext, IngestionPlugin
from ..plugins.analytics_plugin.tasks import AnalyticsPlugin
from ..plugins.audit_plugin.tasks import AuditPlugin


class TestMCPSecureEffectApp(unittest.TestCase):
    """Test suite verifying 3-plugin reference application execution and security bounds."""

    def setUp(self) -> None:
        self.granted_caps = {
            ("mcp:echo", "echo"),
            ("mcp:report", "generate_report"),
            ("mcp:audit", "audit_log"),
        }
        self.broker, self.cas, self.pipeline = build_cortex_effect_runtime(
            granted_capabilities=self.granted_caps,
            valid_generation=1,
            valid_epoch=10,
        )

        self.ingest_plugin = IngestionPlugin(
            PluginManifest(name="ingestion-plugin", version="1.0.0", description="Ingestion", required_capabilities=["mcp:echo"])
        )
        self.analytics_plugin = AnalyticsPlugin(
            PluginManifest(name="analytics-plugin", version="1.0.0", description="Analytics", required_capabilities=["mcp:report"])
        )
        self.audit_plugin = AuditPlugin(
            PluginManifest(name="audit-plugin", version="1.0.0", description="Audit", required_capabilities=["mcp:audit"])
        )

        self.ctx = ExecutionContext(
            invocation_id="inv_test_001",
            resource_id="res_external_mcp",
            lease_epoch=10,
            worker_generation=1,
        )

    def test_ingestion_plugin_succeeds(self) -> None:
        outcome = self.ingest_plugin.ingest_payload(
            pipeline=self.pipeline,
            ctx=self.ctx,
            raw_data={"sensor_id": "S101", "val": 99.8},
            execution_attempt_id="att_test_ingest",
        )

        self.assertEqual(outcome.status, ExecutionStatus.EFFECT_COMMITTED)
        self.assertIsNotNone(outcome.evidence)
        if outcome.evidence:
            self.assertIn("S101", outcome.evidence.data.decode("utf-8"))

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

    def test_audit_plugin_succeeds(self) -> None:
        outcome = self.audit_plugin.run_audit(
            pipeline=self.pipeline,
            ctx=self.ctx,
            execution_attempt_id="att_test_audit",
        )

        self.assertEqual(outcome.status, ExecutionStatus.EFFECT_COMMITTED)
        self.assertIsNotNone(outcome.evidence)
        if outcome.evidence:
            self.assertIn("aud_9901", outcome.evidence.data.decode("utf-8"))

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
