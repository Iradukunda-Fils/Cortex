"""
Execution Graph Builder Service

Consumes: IntentEvent, PlanGeneratedEvent, CommandIssuedEvent,
          DriverTelemetryEvent, VerificationResultEvent (via BaseEvent wildcard)
Produces: (none — pure projection / read model)

Constructs a real-time Directed Acyclic Graph (DAG) from the stream
of kernel messages. Each node is linked to its causal parent via the
message identity fields (intent_id, plan_id, command_id, causation_id).
"""

from typing import Dict, Any
from tools.kernel.graph.execution_graph import ExecutionGraph
from tools.kernel.schema.message import (
    BaseEvent,
    IntentEvent,
    PlanGeneratedEvent,
    CommandIssuedEvent,
    DriverTelemetryEvent,
    VerificationResultEvent,
)


class ExecutionGraphBuilderService:
    def __init__(self):
        self.graphs: Dict[str, ExecutionGraph] = {}

    def record_message(self, msg: Any) -> None:
        if isinstance(msg, IntentEvent):
            graph = ExecutionGraph(root_id=msg.intent_id)
            graph.add_node(
                node_id=msg.intent_id,
                node_type="Intent",
                payload={"goal": msg.goal},
            )
            self.graphs[msg.intent_id] = graph

        elif isinstance(msg, PlanGeneratedEvent):
            graph = self.graphs.get(msg.intent_id)
            if graph:
                graph.add_node(
                    node_id=msg.plan_id,
                    node_type="Plan",
                    payload={"step_count": len(msg.steps)},
                    parent_id=msg.intent_id,
                )

        elif isinstance(msg, CommandIssuedEvent):
            for graph in self.graphs.values():
                if msg.plan_id in graph.nodes:
                    graph.add_node(
                        node_id=msg.command_id,
                        node_type="Command",
                        payload={"action": msg.action, "params": msg.parameters},
                        parent_id=msg.plan_id,
                    )
                    break

        elif isinstance(msg, BaseEvent):
            for graph in self.graphs.values():
                if msg.causation_id and msg.causation_id in graph.nodes:
                    node_type = "Event"
                    payload: Dict[str, Any] = {}
                    if isinstance(msg, DriverTelemetryEvent):
                        node_type = "Telemetry"
                        payload = {"status": msg.status, "data": msg.payload}
                    elif isinstance(msg, VerificationResultEvent):
                        node_type = "Verification"
                        payload = {"passed": msg.passed, "rule": msg.rule_id}

                    graph.add_node(
                        node_id=msg.event_id,
                        node_type=node_type,
                        payload=payload,
                        parent_id=msg.causation_id,
                    )
                    break
