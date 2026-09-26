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


def _star(citers: int = 50) -> nx.DiGraph:
    """`cited` (2020) is cited by every other paper; `old` (2000) by none."""
    g = nx.DiGraph()
    g.add_node("cited", year=2020)
    g.add_node("old", year=2000)
    for i in range(citers):
        g.add_node(f"p{i}", year=2021)
        g.add_edge(f"p{i}", "cited", weight=1.0)
    return g


def test_citation_structure_can_outweigh_age():
    """Raw PageRank sums to 1 over the graph, so with 0.5 * PageRank beside
    0.3 * age the uncited 2000 paper beat a paper every other one cites, and
    edge weighting could not move a top ten (thesis Section 5.6.4). Scaled to
    the top value, citation structure carries the weight it was given."""
    ranked = GraphAnalytics(_star()).rank_foundational_papers(top_n=2)
    assert [r["paper_id"] for r in ranked] == ["cited", "old"]
    assert ranked[0]["influence"] == pytest.approx(1.0)


def test_edge_weights_move_the_ranking():
    """Two papers alike in age and evidence, cited by the same papers: the one
    whose citing edges carry more evidence weight must rank clearly higher.
    The 200 unrelated papers give the graph a realistic size, where raw
    PageRank values are small enough that the old formula barely told the two
    apart."""
    g = nx.DiGraph()
    for node in ("heavy", "light"):
        g.add_node(node, year=2010)
    for i in range(200):
        g.add_node(f"other{i}", year=2010)
    for i in range(20):
        g.add_node(f"c{i}", year=2022)
        g.add_edge(f"c{i}", "heavy", weight=0.9)
        g.add_edge(f"c{i}", "light", weight=0.1)
    top = GraphAnalytics(g).rank_foundational_papers(top_n=2)
    assert [r["paper_id"] for r in top] == ["heavy", "light"]
    assert top[0]["score"] - top[1]["score"] > 0.1


def test_seed_is_not_its_own_foundation():
    """The seed usually has the highest PageRank in its own graph; left in, it
    would head its own list of foundations and set the scale for the rest."""
    g = _star()
    ranked = GraphAnalytics(g).rank_foundational_papers(top_n=60, seed_id="cited")
    assert "cited" not in {r["paper_id"] for r in ranked}
    assert max(r["influence"] for r in ranked) == pytest.approx(1.0)


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
