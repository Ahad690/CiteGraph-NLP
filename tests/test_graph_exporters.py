"""Tests for the graph exporters.

Also at 0% coverage, and reachable from the API: `routes.py` serves
`/runs/{run_id}/export/graphml`. `save_all` writes to a caller-supplied directory,
so its contract is that it creates that directory and writes every file it
promises -- an exporter that writes one of two files is indistinguishable from one
that works, until someone opens the second.
"""
from __future__ import annotations

import json

import networkx as nx
import pytest

from citegraph.graph.exporters import GraphExporter


@pytest.fixture
def chain() -> nx.DiGraph:
    """a -> b -> c, with attributes on both nodes and edges.

    The attributes are the point: node_link_data and write_graphml are only worth
    testing for their round-trip fidelity if the attributes survive.
    """
    g = nx.DiGraph()
    g.add_node("p1", title="First paper", year=2020)
    g.add_node("p2", title="Second paper", year=2021)
    g.add_node("p3", title="Third paper", year=2022)
    g.add_edge("p1", "p2", confidence=0.91)
    g.add_edge("p2", "p3", confidence=0.42)
    return g


class TestToJson:
    def test_is_valid_json(self, chain):
        data = json.loads(GraphExporter(chain).to_json())
        assert isinstance(data, dict)

    def test_preserves_every_node_and_edge(self, chain):
        """Both edge keys are asserted, and they must be the same objects.

        networkx renamed node_link_data's edge array from "links" to "edges" in
        3.4, so the exporter emits both. A file written under one name must be
        readable under the other, and neither may quietly hold a different list.
        """
        data = json.loads(GraphExporter(chain).to_json())
        assert len(data["nodes"]) == 3
        assert len(data["edges"]) == 2
        assert len(data["links"]) == 2
        assert data["edges"] == data["links"]

    def test_declares_the_graph_is_directed(self, chain):
        """A citation graph has direction; saying so lets a consumer check."""
        data = json.loads(GraphExporter(chain).to_json())
        assert data["directed"] is True
        assert data["multigraph"] is False

    def test_preserves_node_attributes(self, chain):
        data = json.loads(GraphExporter(chain).to_json())
        by_id = {n["id"]: n for n in data["nodes"]}
        assert by_id["p1"]["year"] == 2020
        assert by_id["p2"]["title"] == "Second paper"

    def test_preserves_edge_confidence(self, chain):
        """Confidence is the product's core claim; losing it in export is a defect."""
        data = json.loads(GraphExporter(chain).to_json())
        confidences = {link.get("confidence") for link in data["links"]}
        assert confidences == {0.91, 0.42}

    def test_empty_graph(self):
        data = json.loads(GraphExporter(nx.DiGraph()).to_json())
        assert data["nodes"] == []
        assert data["edges"] == []
        assert data["links"] == []

    def test_is_indented_for_review(self, chain):
        """Someone reads this file. A single line is not reviewable."""
        assert "\n" in GraphExporter(chain).to_json()

    def test_two_calls_produce_identical_output(self, chain):
        exporter = GraphExporter(chain)
        assert exporter.to_json() == exporter.to_json()


class TestToGraphml:
    def test_writes_a_readable_file(self, chain, tmp_path):
        out = tmp_path / "graph.graphml"
        GraphExporter(chain).to_graphml(out)
        assert out.is_file()
        assert out.stat().st_size > 0

    def test_round_trips_through_networkx(self, chain, tmp_path):
        out = tmp_path / "graph.graphml"
        GraphExporter(chain).to_graphml(out)
        reloaded = nx.read_graphml(str(out))
        assert reloaded.number_of_nodes() == 3
        assert reloaded.number_of_edges() == 2

    def test_round_trip_keeps_confidence(self, chain, tmp_path):
        """Confidence must survive the round trip, as a number.

        The assertion uses the float value rather than a string because
        networkx 3.6 restores the declared type; it stored every attribute as
        text for several releases before that. Pinning the type here would fail
        on a library downgrade that is otherwise harmless, and the value check
        catches the thing that actually matters: the number is not lost or
        rounded on the way out.
        """
        out = tmp_path / "graph.graphml"
        GraphExporter(chain).to_graphml(out)
        reloaded = nx.read_graphml(str(out))
        confidences = {d["confidence"] for _, _, d in reloaded.edges(data=True)}
        assert confidences == {0.91, 0.42}
        assert all(isinstance(c, float) for c in confidences)

    def test_empty_graph_still_writes(self, tmp_path):
        out = tmp_path / "empty.graphml"
        GraphExporter(nx.DiGraph()).to_graphml(out)
        assert out.is_file()


class TestSaveAll:
    def test_creates_the_directory(self, chain, tmp_path):
        target = tmp_path / "does" / "not" / "exist"
        GraphExporter(chain).save_all(target)
        assert target.is_dir()

    def test_writes_every_promised_file(self, chain, tmp_path):
        """Both files, not one. A partial export looks exactly like a working one."""
        target = tmp_path / "out"
        GraphExporter(chain).save_all(target)
        assert (target / "graph.json").is_file()
        assert (target / "graph.graphml").is_file()

    def test_the_json_it_writes_is_valid(self, chain, tmp_path):
        target = tmp_path / "out"
        GraphExporter(chain).save_all(target)
        data = json.loads((target / "graph.json").read_text(encoding="utf-8"))
        assert len(data["nodes"]) == 3
        assert len(data["links"]) == 2

    def test_the_graphml_it_writes_reloads(self, chain, tmp_path):
        target = tmp_path / "out"
        GraphExporter(chain).save_all(target)
        assert nx.read_graphml(str(target / "graph.graphml")).number_of_edges() == 2

    def test_is_idempotent(self, chain, tmp_path):
        """Re-exporting over an existing directory must not raise."""
        target = tmp_path / "out"
        GraphExporter(chain).save_all(target)
        GraphExporter(chain).save_all(target)
        assert len(json.loads((target / "graph.json").read_text())["nodes"]) == 3

    def test_empty_graph(self, tmp_path):
        target = tmp_path / "out"
        GraphExporter(nx.DiGraph()).save_all(target)
        assert json.loads((target / "graph.json").read_text())["nodes"] == []
