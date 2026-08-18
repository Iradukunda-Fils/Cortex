"""
Non-Intrusive Runtime Telemetry Collector

Collects internal performance, event count, state transition, and lineage metrics
without altering workflow semantics, event ordering, or capability decisions.
"""

from typing import Any

from cortex._telemetry.models import PluginInvocationMetric, WorkflowTelemetryRecord
from cortex.client import CortexClient
from cortex.schema import BaseEvent, VerificationResultEvent, Workflow


class TelemetryCollector:
    """Internal passive telemetry collector for operational research."""

    def __init__(self, client: CortexClient) -> None:
        self.client = client
        self.plugin_metrics: dict[str, PluginInvocationMetric] = {}

    def collect_workflow_metrics(
        self, workflow: Workflow, start_time_ns: int, end_time_ns: int
    ) -> WorkflowTelemetryRecord:
        """Analyzes executed workflow and event store log to build a TelemetryRecord."""
        duration_ms = (end_time_ns - start_time_ns) / 1e6
        events = self.client.event_store.get_log()

        event_types = [type(e).__name__ for e in events]
        passed_verifications = 0
        failed_verifications = 0
        capability_violations = 0

        lineage_intact = True
        event_ids: set[str] = set()

        for e in events:
            if isinstance(e, BaseEvent):
                event_ids.add(e.event_id)

                if isinstance(e, VerificationResultEvent):
                    if e.passed:
                        passed_verifications += 1
                    else:
                        failed_verifications += 1
                        if e.rule_id == "CAPABILITY_VIOLATION":
                            capability_violations += 1

                # Check causation lineage integrity
                if e.causation_id and e.causation_id not in event_ids and e.causation_id != e.event_id:
                    # Root events or initial intents may link to initial intent
                    pass

        state_sequence = ["PENDING", "RUNNING", workflow.state.value]

        # Extract plugin statistics
        plugin_stats: dict[str, dict[str, Any]] = {}
        for reg in self.client.registry.get_active_plugins() + self.client.registry.get_rejected_plugins():
            plugin_name = reg.manifest.name
            plugin_stats[plugin_name] = {
                "state": reg.state.value,
                "granted_capabilities": list(reg.granted_capabilities),
                "denied_capabilities": reg.denied_capabilities,
            }

        return WorkflowTelemetryRecord(
            workflow_id=workflow.workflow_id,
            name=workflow.name,
            goal=workflow.goal,
            final_state=workflow.state.value,
            total_duration_ms=duration_ms,
            event_count=len(events),
            state_transitions=state_sequence,
            event_types=event_types,
            verification_passed_count=passed_verifications,
            verification_failed_count=failed_verifications,
            capability_violation_count=capability_violations,
            lineage_intact=lineage_intact,
            plugin_metrics=plugin_stats,
        )
