"""
Execution Intelligence & Causal Explainer Kernel Service
"""

from cortex.tools.kernel.graph.execution_graph import ExecutionGraph, GraphNode


class CausalExplainer:
    """Analyzes an ExecutionGraph to provide root-cause diagnostics and lineage traces."""
    graph: ExecutionGraph

    def __init__(self, graph: ExecutionGraph):
        self.graph = graph

    def explain_failure(self, failed_node_id: str) -> dict[str, object]:
        """Traverses backwards up the causal chain to locate the root cause of a failure."""
        if failed_node_id not in self.graph.nodes:
            return {"error": "Node not found"}

        chain: list[GraphNode] = []
        curr: str | None = failed_node_id

        while curr and curr in self.graph.nodes:
            node = self.graph.nodes[curr]
            chain.append(node)
            curr = node.parent_id

        chain.reverse()

        return {
            "target_node": failed_node_id,
            "root_intent": chain[0].payload if chain else None,
            "causal_path": [
                {
                    "node_id": n.node_id,
                    "type": n.node_type,
                    "summary": n.payload
                } for n in chain
            ],
            "diagnosis": self._derive_diagnosis(chain)
        }

    def _derive_diagnosis(self, chain: list[GraphNode]) -> str:
        for node in reversed(chain):
            if node.node_type == "Verification" and not node.payload.get("passed", True):
                return f"Verification assertion failed at rule '{node.payload.get('rule')}'."
            if node.node_type == "Telemetry" and node.payload.get("status") != "ok":
                return f"Driver reported error status '{node.payload.get('status')}' during command execution."
        return "Unknown failure cause."
