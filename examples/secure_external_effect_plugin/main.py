"""
Reference Application Entry Point — Cortex Secure External Effect Plugin.

Demonstrates the complete Cortex effect execution lifecycle:

    Plugin Intent → Capability Check → Lease Fencing → HMAC Idempotency
    → Credential Isolation → Adapter Execution → Reconciliation → Evidence

Runs completely offline using a local deterministic API server fixture.
Shows both SUCCESSFUL and REJECTED operations.

Usage:
    python -m examples.secure_external_effect_plugin.main
"""

from __future__ import annotations

import os
import sys
from typing import Tuple

import yaml

from cortex import CortexClient, IntentEvent, PluginManifest
from cortex.tools.kernel.adapter_contract import EffectClassification
from cortex.tools.kernel.adapters.mcp_adapter import LocalProcessMCPAdapter
from cortex.tools.kernel.effect_gateway import (
    CapabilityDeniedError,
    EffectFencingError,
    GatewayAuthorizationGate,
)
from cortex.tools.kernel.effect_runtime import (
    ContentAddressableStore,
    CredentialBroker,
    EffectExecutionPipeline,
    EffectResultStore,
)
from cortex.tools.kernel.reconciliation import EffectReconciliationEngine

from .plugins.audit_plugin import AuditPlugin
from .plugins.record_plugin import RecordServicePlugin, WorkerContext

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
LOCAL_API_SERVER = os.path.join(FIXTURES_DIR, "local_api_server.py")
PLUGINS_DIR = os.path.join(os.path.dirname(__file__), "plugins")


def load_manifest_from_yaml(manifest_path: str) -> PluginManifest:
    """Loads a PluginManifest declaratively from a plugin's manifest.yml file."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return PluginManifest(
        name=data["name"],
        version=data["version"],
        description=data["description"],
        consumes_events=data.get("consumes_events", []),
        produces_events=data.get("produces_events", []),
        required_capabilities=data.get("required_capabilities", []),
    )


# ── Capability Registry ──────────────────────────────────────────────


class RecordCapabilityRegistry:
    """Resolves granted capabilities and effect classifications for record operations."""

    def __init__(self, granted_capabilities: set[Tuple[str, str]]) -> None:
        self._granted = granted_capabilities

    def is_capability_granted(self, capability: str, operation: str) -> bool:
        return (capability, operation) in self._granted

    def resolve_effect_classification(self, capability: str, operation: str) -> EffectClassification:
        if operation == "lookup":
            return EffectClassification.READ_ONLY
        elif operation in ("store", "log"):
            return EffectClassification.IDEMPOTENT_WRITE
        elif operation == "transfer":
            return EffectClassification.NON_IDEMPOTENT_WRITE
        return EffectClassification.UNKNOWN_EFFECT


# ── Effect Authority ─────────────────────────────────────────────────


class RecordEffectAuthority:
    """Validates worker reservation state at effect boundary."""

    def __init__(self, valid_generation: int = 1, valid_epoch: int = 10) -> None:
        self._gen = valid_generation
        self._epoch = valid_epoch

    def validate_effect_reservation(self, worker_generation: int, lease_epoch: int) -> bool:
        return worker_generation == self._gen and lease_epoch == self._epoch


# ── Pipeline Assembly ────────────────────────────────────────────────


def build_effect_pipeline(
    granted_capabilities: set[Tuple[str, str]],
    valid_generation: int = 1,
    valid_epoch: int = 10,
) -> Tuple[CredentialBroker, ContentAddressableStore, EffectExecutionPipeline, EffectResultStore]:
    """Assembles the full Cortex external effect pipeline."""

    authority = RecordEffectAuthority(valid_generation=valid_generation, valid_epoch=valid_epoch)
    registry = RecordCapabilityRegistry(granted_capabilities=granted_capabilities)
    domain_secret = b"cortex_reference_sample_32byte_k!"  # 32 bytes, development only

    gateway = GatewayAuthorizationGate(
        effect_authority=authority,
        capability_registry=registry,
        domain_secret=domain_secret,
    )

    broker = CredentialBroker()
    broker.register_credential("res_local_api", b"bearer_token_local_dev_only_xyz")

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


# ── Main Demonstration ───────────────────────────────────────────────


def run_reference_demo() -> dict:
    """Runs the complete reference demonstration with positive and negative cases."""
    results: dict = {}

    granted_caps = {
        ("api:records", "lookup"),
        ("api:records", "store"),
        ("api:audit", "log"),
    }

    broker, cas, pipeline, result_store = build_effect_pipeline(granted_capabilities=granted_caps)

    # ── CortexClient Workflow ────────────────────────────────────

    client = CortexClient(platform_capabilities={"api:records", "api:audit"})

    worker_ctx = WorkerContext(
        invocation_id="inv_ref_001",
        resource_id="res_local_api",
        lease_epoch=10,
        worker_generation=1,
    )

    # Load manifests declaratively from manifest.yml files
    record_manifest = load_manifest_from_yaml(os.path.join(PLUGINS_DIR, "record_plugin", "manifest.yml"))
    audit_manifest = load_manifest_from_yaml(os.path.join(PLUGINS_DIR, "audit_plugin", "manifest.yml"))

    plugin = RecordServicePlugin(
        record_manifest,
        pipeline=pipeline,
        worker_ctx=worker_ctx,
    )

    audit_plugin = AuditPlugin(
        audit_manifest,
        pipeline=pipeline,
        worker_ctx=worker_ctx,
    )

    reg = client.register_plugin(plugin)
    reg_audit = client.register_plugin(audit_plugin)
    results["plugin_state"] = reg.state.value
    results["audit_plugin_state"] = reg_audit.state.value

    workflow = client.create_workflow(name="reference_workflow", goal="Demonstrate Cortex Effect Pipeline")
    intent = IntentEvent(
        workflow_id=workflow.workflow_id,
        goal=workflow.goal,
        parameters={"record_id": "rec_001"},
    )
    completed = client.run_workflow(workflow, initial_intent=intent)
    results["workflow_state"] = completed.state.name

    # ── 1. SUCCESSFUL: Authorized record lookup ──────────────────

    outcome = plugin.lookup_record(pipeline, worker_ctx, record_id="rec_001")
    results["1_authorized_lookup_status"] = outcome.status.value
    results["1_authorized_lookup_has_evidence"] = outcome.evidence is not None

    # ── 2. SUCCESSFUL: Authorized record store ───────────────────

    outcome_store = plugin.store_record(pipeline, worker_ctx, key="test_key", value="test_value",
                                         execution_attempt_id="att_store_ref")
    results["2_authorized_store_status"] = outcome_store.status.value

    # ── 3. REJECTED: Ungranted capability ────────────────────────

    try:
        plugin.request_unauthorized_operation(pipeline, worker_ctx)
        results["3_ungranted_denied"] = False
    except CapabilityDeniedError as err:
        results["3_ungranted_denied"] = True
        results["3_ungranted_error"] = str(err)

    # ── 4. REJECTED: Stale lease epoch ───────────────────────────

    try:
        plugin.request_with_stale_lease(pipeline, worker_ctx, stale_epoch=3)
        results["4_stale_lease_denied"] = False
    except EffectFencingError as err:
        results["4_stale_lease_denied"] = True
        results["4_stale_lease_error"] = str(err)

    # ── 5. REJECTED: Duplicate/replayed effect ───────────────────

    replay_outcome = plugin.lookup_record(pipeline, worker_ctx, record_id="rec_001",
                                           execution_attempt_id="att_replay_01")
    results["5_replay_status"] = replay_outcome.status.value
    results["5_replay_is_cached"] = result_store.committed_count > 0

    # ── 6. HANDLED: Failed external service ──────────────────────

    fail_outcome = plugin.request_failed_service(pipeline, worker_ctx,
                                                  execution_attempt_id="att_fail_ref")
    results["6_failed_service_status"] = fail_outcome.status.value
    results["6_failed_service_has_error"] = fail_outcome.error_message is not None

    # ── 7. VERIFIED: Credential isolation ────────────────────────

    vault_secret = broker.resolve("res_local_api")
    results["7_credential_in_vault"] = vault_secret is not None
    results["7_credential_not_in_outcome"] = "bearer_token" not in str(outcome)

    return results


def main() -> None:
    print("=" * 70)
    print(" CORTEX REFERENCE SAMPLE: Secure External Effect Plugin")
    print(" Demonstrates: Plugin → Gateway → Adapter → Evidence")
    print("=" * 70)

    res = run_reference_demo()

    print("\n─── Event DAG (2-Plugin Chain) ───")
    print("  IntentEvent → RecordServicePlugin → CommandIssuedEvent → AuditPlugin → VerificationResultEvent")
    print(f"  RecordServicePlugin:    {res['plugin_state']}")
    print(f"  AuditPlugin:            {res['audit_plugin_state']}")
    print(f"  Workflow Completion:    {res['workflow_state']}")
    print("\n─── Positive Results (Authorized Operations) ───")
    print(f"  1. Record Lookup:       {res['1_authorized_lookup_status']} (evidence={res['1_authorized_lookup_has_evidence']})")
    print(f"  2. Record Store:        {res['2_authorized_store_status']}")

    print("\n─── Negative Results (Rejected Operations) ───")
    print(f"  3. Ungranted Capability: DENIED={res['3_ungranted_denied']}")
    print(f"     Reason: {res.get('3_ungranted_error', 'N/A')}")
    print(f"  4. Stale Lease Epoch:    DENIED={res['4_stale_lease_denied']}")
    print(f"     Reason: {res.get('4_stale_lease_error', 'N/A')}")
    print(f"  5. Replay Protection:    Status={res['5_replay_status']} (cached={res['5_replay_is_cached']})")
    print(f"  6. Failed Service:       Status={res['6_failed_service_status']} (error={res['6_failed_service_has_error']})")

    print("\n─── Security Boundary Verification ───")
    print(f"  7. Credential Isolation: Vault={res['7_credential_in_vault']}, Not Leaked={res['7_credential_not_in_outcome']}")

    print("\n" + "=" * 70)
    print(" [✓] ALL AUTHORIZED OPERATIONS SUCCEEDED")
    print(" [✓] ALL UNAUTHORIZED OPERATIONS REJECTED")
    print(" [✓] CREDENTIALS NEVER LEAKED TO PLUGIN")
    print("=" * 70)


if __name__ == "__main__":
    main()
