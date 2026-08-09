"""
Public CortexClient API

Main developer-facing entrypoint for orchestrating workflows, registering plugins,
enforcing capability sandboxes, inspecting traces, and executing deterministic replay.
"""

import json
import os
from typing import cast

from cortex.plugin import BasePlugin, PluginContext
from cortex.schema.events import (
    BaseEvent,
    IntentEvent,
    VerificationResultEvent,
    Workflow,
    WorkflowPolicy,
    WorkflowState,
    dict_to_event,
    event_to_dict,
)
from cortex.tools.kernel.graph.analyzer import ExecutionGraphAnalyzer
from cortex.tools.kernel.plugin.loader import (
    PluginRegistration,
    PluginRegistry,
    PluginState,
)
from cortex.tools.kernel.services.event_store import EventStoreService
from cortex.tools.kernel.services.graph_builder import ExecutionGraphBuilderService
from cortex.tools.kernel.services.replay import DeterministicReplayEngine
from cortex.tools.kernel.transport import AnyEvent, EventHandler, InMemoryTransport


class CortexClient:
    """Public high-level Python API for Cortex execution runtime."""

    platform_capabilities: set[str]
    registry: PluginRegistry
    transport: InMemoryTransport
    event_store: EventStoreService
    graph_builder: ExecutionGraphBuilderService
    registered_plugins: list[BasePlugin]

    def __init__(self, platform_capabilities: set[str] | None = None) -> None:
        if platform_capabilities is None:
            # Default standard platform capabilities
            self.platform_capabilities = {
                "workflow.plan.create",
                "workflow.command.issue",
                "hardware.telemetry.read",
                "verification.oracle.execute",
                "verification.invariant.check",
                "fs:read",
                "exec:git",
                "exec:pytest",
            }
        else:
            self.platform_capabilities = set(platform_capabilities)

        self.registry = PluginRegistry(self.platform_capabilities)
        self.transport = InMemoryTransport()
        self.event_store = EventStoreService()
        self.graph_builder = ExecutionGraphBuilderService()
        self.registered_plugins = []

        # Wire global stores using named def handlers to satisfy lint & type checkers
        def store_handler(e: AnyEvent) -> None:
            self.event_store.record_event(e)

        def builder_handler(e: AnyEvent) -> None:
            self.graph_builder.record_message(e)

        self.transport.subscribe(BaseEvent, store_handler)
        self.transport.subscribe(BaseEvent, builder_handler)

    def register_plugin(self, plugin: BasePlugin) -> PluginRegistration:
        """Register a plugin with capability negotiation."""
        registration = self.registry.register(plugin.manifest)
        if registration.state == PluginState.ACTIVE:
            context = PluginContext(
                session_id="default_session",
                granted_capabilities=registration.granted_capabilities,
                publish_func=self.transport.publish,
            )
            plugin.set_context(context)

            def create_plugin_handler(p: BasePlugin) -> EventHandler:
                def plugin_handler(e: AnyEvent) -> None:
                    self._dispatch_to_plugin(p, e)
                return plugin_handler

            for _ in plugin.manifest.consumes_events:
                self.transport.subscribe(BaseEvent, create_plugin_handler(plugin))

        self.registered_plugins.append(plugin)
        return registration

    def _dispatch_to_plugin(self, plugin: BasePlugin, event: AnyEvent) -> None:
        """Helper to safely dispatch event to plugin if active and consuming."""
        if plugin.context and isinstance(event, BaseEvent) and type(event).__name__ in plugin.manifest.consumes_events:
            plugin.on_event(event)

    def create_workflow(self, name: str, goal: str, policy: WorkflowPolicy | None = None) -> Workflow:
        """Instantiate a new Workflow primitive."""
        if policy is None:
            policy = WorkflowPolicy()
        return Workflow(name=name, goal=goal, policy=policy)

    def run_workflow(self, workflow: Workflow, initial_intent: IntentEvent | None = None) -> Workflow:
        """Executes a workflow from PENDING to RUNNING to COMPLETED or FAILED."""
        workflow.state = WorkflowState.RUNNING

        # Verify whether any registered plugin was REJECTED during negotiation
        rejected = self.registry.get_rejected_plugins()
        if rejected:
            denied_caps: list[str] = []
            for r in rejected:
                denied_caps.extend(r.denied_capabilities)

            violation_event = VerificationResultEvent(
                workflow_id=workflow.workflow_id,
                passed=False,
                rule_id="CAPABILITY_VIOLATION",
                details={
                    "reason": f"Plugins rejected due to unauthorized capabilities: {denied_caps}",
                    "rejected_plugins": [r.manifest.name for r in rejected],
                },
            )
            self.transport.publish(violation_event)
            workflow.state = WorkflowState.FAILED
            return workflow

        if initial_intent is None:
            initial_intent = IntentEvent(workflow_id=workflow.workflow_id, goal=workflow.goal)

        self.transport.publish(initial_intent)

        # Check for any failed verification events in store
        failed_verifications = [
            e for e in self.event_store.get_log()
            if isinstance(e, VerificationResultEvent) and not e.passed
        ]

        if failed_verifications:
            workflow.state = WorkflowState.FAILED
        else:
            workflow.state = WorkflowState.COMPLETED

        return workflow

    def inspect_workflow(self, trace_or_id: str) -> dict[str, str | int | list[str] | list[dict[str, object]]]:
        """Inspects an execution trace and provides graph lineage and root cause analysis."""
        events = self._resolve_events(trace_or_id)

        builder = ExecutionGraphBuilderService()
        for e in events:
            builder.record_message(e)

        graph = list(builder.graphs.values())[0] if builder.graphs else None

        failed_nodes: list[dict[str, object]] = []
        causality_tree: list[str] = []
        wf_name = "Inspected Workflow"
        wf_goal = "Trace Inspection"

        if os.path.exists(trace_or_id):
            with open(trace_or_id, "r", encoding="utf-8") as f:
                raw_data = cast(object, json.load(f))
                if isinstance(raw_data, dict):
                    data = cast(dict[str, object], raw_data)
                    wf_name = str(data.get("name", wf_name))
                    wf_goal = str(data.get("goal", wf_goal))

        if graph:
            analyzer = ExecutionGraphAnalyzer(graph)
            for node in analyzer.find_failed_nodes():
                failed_nodes.append({
                    "id": node.node_id,
                    "type": node.node_type,
                    "payload": node.payload,
                    "parent_id": node.parent_id,
                })

            for node_id, node in graph.nodes.items():
                parent_info = f" -> parent: {node.parent_id[:8]}" if node.parent_id else " (ROOT)"
                causality_tree.append(f"[{node.node_type}] ID: {node_id[:8]}{parent_info} | {node.payload}")

        return {
            "name": wf_name,
            "goal": wf_goal,
            "total_events": len(events),
            "node_count": len(graph.nodes) if graph else 0,
            "failed_nodes": failed_nodes,
            "causality_tree": causality_tree,
        }

    def replay_workflow(self, trace_or_id: str) -> dict[str, str | int | bool]:
        """Replays an event journal and asserts 100% causal sequence immutability."""
        events = self._resolve_events(trace_or_id)

        replay_transport = InMemoryTransport()
        replayed_events: list[BaseEvent] = []

        def replay_handler(e: AnyEvent) -> None:
            if isinstance(e, BaseEvent):
                replayed_events.append(e)

        replay_transport.subscribe(BaseEvent, replay_handler)

        engine = DeterministicReplayEngine(replay_transport)
        count = engine.replay_journal(events)
        result = engine.verify_replayed_lineage(events, replayed_events)

        return {
            "replayed_count": count,
            "deterministic": cast(bool, result.get("match", False)),
            "reason": cast(str, result.get("reason", "")),
        }

    def save_trace(self, workflow_id: str, filepath: str, name: str = "Workflow", goal: str = "Execution") -> str:
        """Saves current event store log to JSON file."""
        events = self.event_store.get_log()
        serialized: list[dict[str, object]] = []
        for e in events:
            if isinstance(e, BaseEvent):
                serialized.append(event_to_dict(e))

        payload: dict[str, object] = {
            "name": name,
            "goal": goal,
            "workflow_id": workflow_id,
            "event_count": len(serialized),
            "events": serialized,
        }

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return filepath

    def _resolve_events(self, trace_or_id: str) -> list[BaseEvent]:
        """Resolves file path or in-memory event log."""
        if os.path.exists(trace_or_id):
            with open(trace_or_id, "r", encoding="utf-8") as f:
                raw_data = cast(object, json.load(f))
                if isinstance(raw_data, dict):
                    data = cast(dict[str, object], raw_data)
                    raw_events: object = data.get("events", [])
                    if isinstance(raw_events, list):
                        events_list = cast(list[object], raw_events)
                        events_dict_list: list[dict[str, object]] = [
                            cast(dict[str, object], item) for item in events_list if isinstance(item, dict)
                        ]
                        return [dict_to_event(e) for e in events_dict_list]

        cortex_path = os.path.join(os.getcwd(), ".cortex", "events", f"{trace_or_id}.json")
        if os.path.exists(cortex_path):
            return self._resolve_events(cortex_path)

        # Fallback to current in-memory log
        return [e for e in self.event_store.get_log() if isinstance(e, BaseEvent)]
