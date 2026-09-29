"""Export a citation graph to the formats the API serves.

The JSON shape is pinned here rather than handed straight to
``nx.node_link_data``. NetworkX renamed the edge array from ``links`` to
``edges`` in 3.4, so a file written by one version of the library is not
readable by another with the same code, and an exported graph is a thing
people keep. Both keys are emitted so a consumer written against either
convention still works, and the key names are asserted in
tests/test_graph_exporters.py so a future rename is caught rather than
discovered by a user with an old file.
"""
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
        # node_link_data names the edge array "edges" on networkx>=3.4 and
        # "links" before that. Emit both so the file survives either consumer.
        edges = data.get("edges", data.get("links", []))
        data["edges"] = edges
        data["links"] = edges
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
