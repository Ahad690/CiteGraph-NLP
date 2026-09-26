"""Does weighting the citation edges change which papers rank as foundational?

RQ3 asks whether evidence weighting produces a defensible ranking, and no run
had compared it with the unweighted alternative. This script runs the pipeline
on the three evaluation seeds, keeps the graph each run builds, and ranks that
same graph six ways, every one leaving out the seed itself:

    current          0.5 * scaled weighted PageRank + 0.3 * age + 0.2 * evidence
    before_fix       the same with raw PageRank, as the system ranked until
                     2026-09-26 (thesis Section 5.6.4)
    no_pagerank      0.3 * age + 0.2 * evidence
    unweighted_pr    the current formula with every edge weight set to 1
    pagerank_w       weighted PageRank alone
    pagerank_u       unweighted PageRank alone

"Scaled" divides by the largest PageRank among the ranked papers. The script
reports how much of each top paper's score the PageRank term supplies and how
far each variant's top ten moves from the current one.

    python scripts/compare_rankings.py            # -> thesis/evidence/ranking_comparison.json
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import statistics
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import networkx as nx  # noqa: E402

import citegraph.pipeline.orchestrator as orchestrator_module  # noqa: E402
from citegraph.graph.analytics import GraphAnalytics  # noqa: E402
from citegraph.models.paper import PaperQuery  # noqa: E402

SEEDS = ["10.1056/NEJMoa2002032", "10.1038/s41586-021-03819-2", "10.1056/NEJMoa1911303"]
MAX_PAPERS = 100
TOP = 10
OUT = os.path.join(ROOT, "thesis", "evidence", "ranking_comparison.json")

captured: list[nx.DiGraph] = []


class CapturingAnalytics(GraphAnalytics):
    def __init__(self, graph):
        captured.append(graph)
        super().__init__(graph)


def components(graph: nx.DiGraph, weighted: bool, seed: str) -> dict[str, dict[str, float]]:
    """The three terms of rank_foundational_papers, computed the same way."""
    pagerank = nx.pagerank(graph, weight="weight" if weighted else None)
    pagerank = {node: value for node, value in pagerank.items() if node != seed}
    top = max(pagerank.values())
    year_now = datetime.now(timezone.utc).year
    terms = {}
    for node, influence in pagerank.items():
        data = graph.nodes[node]
        year = data.get("year")
        year_score = min(1.0, (year_now - year) / 20.0) if year else 0.5
        n_eff = data.get("n_eff") or 0
        confidence = data.get("population_confidence") or 0.5
        evidence = math.log1p(n_eff) / math.log1p(100000) * confidence
        terms[node] = {"pagerank": influence, "scaled": influence / top, "age": year_score, "evidence": evidence}
    return terms


def ranked(scores: dict[str, float]) -> list[str]:
    return [node for node, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)]


def spearman(a: list[str], b: list[str]) -> float:
    rank_b = {node: i for i, node in enumerate(b)}
    n = len(a)
    d2 = sum((i - rank_b[node]) ** 2 for i, node in enumerate(a))
    return 1 - 6 * d2 / (n * (n * n - 1))


async def run_seed(seed: str) -> dict:
    orchestrator = orchestrator_module.PipelineOrchestrator()
    result = await orchestrator.run(PaperQuery(query_type="doi", value=seed),
                                    backward_depth=2, forward_depth=1, max_papers=MAX_PAPERS)
    graph = captured[-1]
    seed_id = result.seed_paper_id
    weighted, unweighted = components(graph, True, seed_id), components(graph, False, seed_id)
    variants = {
        "current": {n: .5 * t["scaled"] + .3 * t["age"] + .2 * t["evidence"] for n, t in weighted.items()},
        "before_fix": {n: .5 * t["pagerank"] + .3 * t["age"] + .2 * t["evidence"] for n, t in weighted.items()},
        "no_pagerank": {n: .3 * t["age"] + .2 * t["evidence"] for n, t in weighted.items()},
        "unweighted_pr": {n: .5 * t["scaled"] + .3 * t["age"] + .2 * t["evidence"] for n, t in unweighted.items()},
        "pagerank_w": {n: t["pagerank"] for n, t in weighted.items()},
        "pagerank_u": {n: t["pagerank"] for n, t in unweighted.items()},
    }
    orders = {name: ranked(scores) for name, scores in variants.items()}

    # The reimplementation must reproduce the system's own ranking, or every
    # comparison below is against the wrong baseline.
    system_top = [p["paper_id"] for p in result.ranked_foundational_papers][:TOP]
    assert orders["current"][:TOP] == system_top, (orders["current"][:TOP], system_top)

    top = orders["current"][:TOP]
    shares = [.5 * weighted[n]["scaled"] / variants["current"][n] for n in top]
    old_top = orders["before_fix"][:TOP]
    old_shares = [.5 * weighted[n]["pagerank"] / variants["before_fix"][n] for n in old_top]
    weights = [d.get("weight", 1.0) for _, _, d in graph.edges(data=True)]
    title = lambda n: graph.nodes[n].get("title")
    return {
        "seed": seed,
        "nodes": graph.number_of_nodes(), "edges": graph.number_of_edges(),
        "edge_weight": {"min": min(weights), "median": statistics.median(weights), "max": max(weights),
                        "distinct": len({round(w, 6) for w in weights})},
        "pagerank_term_share_of_top10_score": {"median": statistics.median(shares), "max": max(shares)},
        "pagerank_term_share_before_fix": {"median": statistics.median(old_shares), "max": max(old_shares)},
        "largest_pagerank_term_before_fix": max(.5 * t["pagerank"] for t in weighted.values()),
        "median_age_term": statistics.median(.3 * t["age"] for t in weighted.values()),
        "top10_overlap_with_current": {name: len(set(order[:TOP]) & set(top))
                                       for name, order in orders.items() if name != "current"},
        "top10_identical_order": {name: order[:TOP] == top
                                  for name, order in orders.items() if name != "current"},
        "spearman_with_current": {name: round(spearman(orders["current"], order), 4)
                                  for name, order in orders.items() if name != "current"},
        "pagerank_w_vs_u": {"top10_overlap": len(set(orders["pagerank_w"][:TOP]) & set(orders["pagerank_u"][:TOP])),
                            "spearman": round(spearman(orders["pagerank_w"], orders["pagerank_u"]), 4)},
        "top10": {name: [{"paper_id": n, "title": title(n), "year": graph.nodes[n].get("year"),
                          "n_eff": graph.nodes[n].get("n_eff")} for n in order[:TOP]]
                  for name, order in orders.items()},
    }


async def main() -> int:
    orchestrator_module.GraphAnalytics = CapturingAnalytics
    runs = []
    for seed in SEEDS:
        run = await run_seed(seed)
        runs.append(run)
        print(f"{seed}: {run['nodes']} nodes, {run['edges']} edges, "
              f"PageRank share of a top-10 score: median {run['pagerank_term_share_of_top10_score']['median']:.3f} (was {run['pagerank_term_share_before_fix']['median']:.3f})")
        print(f"    top-10 overlap with current: {run['top10_overlap_with_current']}")
        print(f"    same order as current:       {run['top10_identical_order']}")
        print(f"    weighted vs unweighted PageRank alone: {run['pagerank_w_vs_u']}")
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "max_papers": MAX_PAPERS,
                   "runs": runs}, fh, indent=1, ensure_ascii=False)
    print(f"written -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
