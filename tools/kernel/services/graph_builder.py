"""
Execution Graph Builder Service
"""

from typing import Dict, Any
from tools.kernel.graph.execution_graph import ExecutionGraph
from tools.kernel.schema.message import Intent, Plan, Command, Event, DriverTelemetryEvent, VerificationResultEvent

class ExecutionGraphBuilderService:
    def __init__(self):
        self.graphs: Dict[str, ExecutionGraph] = {}

    def record_message(self, msg: Any) -> None:
        if isinstance(msg, Intent):
            graph = ExecutionGraph(root_id=msg.intent_id)
            graph.add_node(node_id=msg.intent_id, node_type="Intent", payload={"goal": msg.goal})
            self.graphs[msg.intent_id] = graph

        elif isinstance(msg, Plan):
            graph = self.graphs.get(msg.intent_id)
            if graph:
                graph.add_node(
                    node_id=msg.plan_id,
                    node_type="Plan",
                    payload={"step_count": len(msg.steps)},
                    parent_id=msg.intent_id
                )

        elif isinstance(msg, Command):
            for graph in self.graphs.values():
                if msg.plan_id in graph.nodes:
                    graph.add_node(
                        node_id=msg.command_id,
                        node_type="Command",
                        payload={"action": msg.action, "params": msg.parameters},
                        parent_id=msg.plan_id
                    )
                    break

        elif isinstance(msg, Event):
            for graph in self.graphs.values():
                if msg.causation_id in graph.nodes:
                    node_type = "Event"
                    payload = {}
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
                        parent_id=msg.causation_id
                    )
                    break
