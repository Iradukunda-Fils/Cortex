"""
Real-Time Causal Execution Graph Representation & Tree Renderer
"""

from dataclasses import dataclass, field


@dataclass
class GraphNode:
    node_id: str
    node_type: str
    payload: dict[str, object]
    parent_id: str | None = None
    children: list[str] = field(default_factory=list)


class ExecutionGraph:
    """First-class Causal Execution Graph representation."""

    root_id: str
    nodes: dict[str, GraphNode]

    def __init__(self, root_id: str):
        self.root_id = root_id
        self.nodes = {}

    def add_node(self, node_id: str, node_type: str, payload: dict[str, object], parent_id: str | None = None) -> None:
        node = GraphNode(node_id=node_id, node_type=node_type, payload=payload, parent_id=parent_id)
        self.nodes[node_id] = node
        if parent_id and parent_id in self.nodes:
            self.nodes[parent_id].children.append(node_id)

    def render_tree(self, current_id: str | None = None, depth: int = 0) -> str:
        """Renders an ASCII tree representation of the execution lineage."""
        if current_id is None:
            current_id = self.root_id
        if current_id not in self.nodes:
            return ""

        node = self.nodes[current_id]
        indent = "  " * depth
        prefix = "└── " if depth > 0 else ""
        result = f"{indent}{prefix}[{node.node_type}] ID: {node.node_id[:8]}.. | Details: {node.payload}\n"
        for child_id in node.children:
            result += self.render_tree(child_id, depth + 1)
        return result
