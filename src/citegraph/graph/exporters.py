import json
import networkx as nx
from pathlib import Path
from typing import Any

class GraphExporter:
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph

    def to_json(self) -> str:
        """Export graph to Cytoscape-compatible JSON or similar."""
        data = nx.node_link_data(self.graph)
        return json.dumps(data, indent=2)

    def to_graphml(self, path: Path):
        """Export graph to GraphML format."""
        nx.write_graphml(self.graph, str(path))

    def save_all(self, output_dir: Path):
        """Save graph in multiple formats."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(output_dir / "graph.json", "w") as f:
            f.write(self.to_json())
            
        self.to_graphml(output_dir / "graph.graphml")
