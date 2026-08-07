"""
Execution Graph Query, Root-Cause Analysis & Divergence Detection Engine
"""

from typing import Dict, List, Optional, Any
from tools.kernel.graph.execution_graph import ExecutionGraph, GraphNode

class ExecutionGraphAnalyzer:
    """Provides analytical, root-cause, and graph-differencing capabilities."""

    def __init__(self, graph: ExecutionGraph):
        self.graph = graph

    def find_root_cause(self, node_id: str) -> List[GraphNode]:
        """Traverses upstream parent pointers to trace lineage back to the root Intent."""
        path: List[GraphNode] = []
        current_id: Optional[str] = node_id

        while current_id and current_id in self.graph.nodes:
            node = self.graph.nodes[current_id]
            path.append(node)
            current_id = node.parent_id

        return path

    def filter_by_type(self, node_type: str) -> List[GraphNode]:
        """Returns all nodes matching the specified type."""
        return [node for node in self.graph.nodes.values() if node.node_type == node_type]

    def find_failed_nodes(self) -> List[GraphNode]:
        """Finds any Verification node where passed == False."""
        failed = []
        for node in self.graph.nodes.values():
            if node.node_type == "Verification" and not node.payload.get("passed", True):
                failed.append(node)
        return failed

    @staticmethod
    def diff_graphs(golden: ExecutionGraph, candidate: ExecutionGraph) -> Dict[str, Any]:
        """Compares a golden reference graph against a candidate execution graph."""
        golden_node_types = [n.node_type for n in golden.nodes.values()]
        candidate_node_types = [n.node_type for n in candidate.nodes.values()]

        node_count_diff = len(candidate.nodes) - len(golden.nodes)
        missing_types = [t for t in golden_node_types if t not in candidate_node_types]

        return {
            "identical_structure": len(golden.nodes) == len(candidate.nodes) and not missing_types,
            "node_count_diff": node_count_diff,
            "missing_node_types": missing_types
        }
