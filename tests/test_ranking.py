"""Regression tests for the foundational paper ranking.

Why this exists: NetworkX 3.x dropped the pure-Python PageRank fallback in
favor of SciPy sparse-matrix routines. Without SciPy installed, the
pipeline crashes at the rank_foundational_papers step with
``ModuleNotFoundError: No module named 'scipy'``. This test fails loudly
if SciPy is missing or PageRank stops being importable.
"""

from __future__ import annotations

import networkx as nx
import pytest

from citegraph.graph.analytics import GraphAnalytics


def test_scipy_is_importable():
    """The pipeline relies on SciPy (transitively via NetworkX PageRank)."""
    import importlib
    importlib.import_module("scipy")
    importlib.import_module("scipy.sparse")


def test_pagerank_runs_on_small_graph():
    """Direct sanity check: NetworkX PageRank must execute without raising."""
    g = nx.DiGraph()
    g.add_edge("A", "B", weight=1.0)
    g.add_edge("B", "C", weight=1.0)
    g.add_edge("C", "A", weight=1.0)
    pr = nx.pagerank(g, weight="weight")
    assert set(pr.keys()) == {"A", "B", "C"}
    assert all(0.0 <= v <= 1.0 for v in pr.values())


def test_rank_foundational_papers_on_small_graph():
    """End-to-end ranking on a 3-paper graph: must produce ranked results
    with monotonically non-increasing scores and no SciPy/NumPy/NetworkX
    runtime errors."""
    g = nx.DiGraph()
    g.add_node("seed", year=2022, n_eff=500, population_confidence=0.9)
    g.add_node("middle", year=2015, n_eff=300, population_confidence=0.8)
    g.add_node("old", year=2000, n_eff=200, population_confidence=0.7)
    g.add_edge("seed", "middle", weight=0.8)
    g.add_edge("middle", "old", weight=0.7)
    g.add_edge("seed", "old", weight=0.5)

    analytics = GraphAnalytics(g)
    ranked = analytics.rank_foundational_papers(top_n=10)

    # Must produce one entry per node
    assert len(ranked) == 3
    ids = {r["paper_id"] for r in ranked}
    assert ids == {"seed", "middle", "old"}

    # Each entry has the documented fields
    for r in ranked:
        assert "score" in r
        assert "explanation" in r
        assert 0.0 <= r["score"] <= 1.5  # combined score, year bonus etc.

    # Sorted by score descending
    scores = [r["score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_rank_foundational_papers_empty_graph_returns_empty():
    """An empty graph must not crash — used as the regression case for the
    early-return guard in rank_foundational_papers."""
    analytics = GraphAnalytics(nx.DiGraph())
    assert analytics.rank_foundational_papers() == []


def test_rank_paths_returns_frontend_compatible_shape():
    g = nx.DiGraph()
    g.add_node("seed", title="Seed Paper")
    g.add_node("middle", title="Middle Paper")
    g.add_node("old", title="Old Paper")
    g.add_edge("seed", "middle", weight=0.8, confidence=0.9)
    g.add_edge("middle", "old", weight=0.7, confidence=0.8)

    ranked = GraphAnalytics(g).rank_paths("seed", top_n=10)

    assert ranked
    first = ranked[0]
    assert first["rank"] == 1
    assert first["paper_ids"] == first["path"]
    assert first["path_score"] == first["score"]
    assert first["path_length"] == len(first["paper_ids"]) - 1
    assert isinstance(first["edge_weights"], list)
    assert 0.0 <= first["average_confidence"] <= 1.0
