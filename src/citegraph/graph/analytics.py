import heapq
import logging
import networkx as nx
from datetime import datetime, timezone
from typing import List, Dict, Any
import math

logger = logging.getLogger(__name__)


class GraphAnalytics:
    # Safety valve: a densely interlinked citation graph can contain an
    # astronomical number of simple paths. Stop enumerating well before that
    # rather than letting a single run stall the whole analysis.
    MAX_PATHS_EXAMINED = 50_000

    def __init__(self, graph: nx.DiGraph):
        self.graph = graph

    def rank_foundational_papers(self, top_n: int = 10, seed_id: str | None = None) -> List[Dict[str, Any]]:
        """Rank papers by their 'foundational' score using citation influence and evidence strength.

        `seed_id` is left out of the ranking: the paper a run starts from is
        not one of its own foundations, and it usually has the highest
        PageRank in the graph, so keeping it would also set the scale below.
        """
        if not self.graph.nodes:
            return []

        # PageRank provides citation influence. Its values sum to 1 over the
        # graph, so in a 100-paper graph a typical paper scores about 0.01
        # while the age and evidence terms run to 1. Used raw, the 0.5 weight
        # gave citation structure about 1% of a top paper's score, and
        # replacing the evidence-weighted edges with unweighted ones left every
        # top ten unchanged (thesis Section 5.6.4). Dividing by the largest
        # value among the ranked papers puts influence on the same 0-1 scale.
        pagerank = nx.pagerank(self.graph, weight='weight')
        pagerank = {node: value for node, value in pagerank.items() if node != seed_id}
        if not pagerank:
            return []
        top_pagerank = max(pagerank.values()) or 1.0

        # Calculate a combined score
        # Foundational papers are:
        # 1. Heavily cited (PageRank)
        # 2. Older (Year bonus)
        # 3. High evidence quality (N_eff and confidence)
        
        # Derived, not hardcoded: a pinned year silently skews the age bonus
        # for every paper once the calendar moves past it.
        current_year = datetime.now(timezone.utc).year
        
        results = []
        for paper_id, raw_pagerank in pagerank.items():
            influence_score = raw_pagerank / top_pagerank
            node_data = self.graph.nodes[paper_id]
            
            # Year score: older is better for foundational
            year = node_data.get("year")
            year_score = 0.5
            if year:
                # Papers older than 10 years get max bonus
                years_old = current_year - year
                year_score = min(1.0, years_old / 20.0)
            
            # Evidence score
            n_eff = node_data.get("n_eff") or 0
            n_score = math.log1p(n_eff) / math.log1p(100000)
            conf = node_data.get("population_confidence") or 0.5
            evidence_score = n_score * conf
            
            # Combined score
            final_score = (0.5 * influence_score) + (0.3 * year_score) + (0.2 * evidence_score)
            
            evidence_description = ("population evidence" if n_eff else "no comparable clinical-population evidence")
            results.append({
                "paper_id": paper_id,
                "title": node_data.get("title"),
                "year": year,
                "score": final_score,
                "influence": influence_score,
                "pagerank": raw_pagerank,
                "n_eff": n_eff,
                "explanation": f"Ranked foundational based on citation influence ({influence_score:.2f}), year ({year}), and {evidence_description}."
            })
            
        return sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]

    def _iter_paths(self, seed_id: str, cutoff: int = 4):
        """Yield every simple path leaving the seed, in a single traversal.

        Calling ``nx.all_simple_paths(seed, target)`` once per target re-walks
        the entire reachable subgraph for every node in the graph, so the cost
        is multiplied by the node count while producing the same set of paths.
        One depth-limited DFS yields each path exactly once.
        """
        stack = [[seed_id]]
        while stack:
            path = stack.pop()
            if len(path) > 1:
                yield path
            if len(path) - 1 >= cutoff:
                continue
            for successor in self.graph.successors(path[-1]):
                # Paths are at most cutoff+1 long, so a scan beats a set here.
                if successor not in path:
                    stack.append(path + [successor])

    def _score_path(self, path: List[str]) -> tuple:
        """Return (score, edge_weights, edge_confidences) for one citation path."""
        edge_weights = []
        edge_confidences = []
        for i in range(len(path) - 1):
            edge_data = self.graph.get_edge_data(path[i], path[i + 1]) or {}
            edge_weights.append(edge_data.get('weight', 1.0))
            edge_confidences.append(edge_data.get('confidence', 1.0))

        avg_weight = sum(edge_weights) / len(edge_weights)
        path_confidence = 1.0
        for c in edge_confidences:
            path_confidence *= c

        depth_bonus = 1.0 / (len(path) ** 0.5)
        return avg_weight * path_confidence * depth_bonus, edge_weights, edge_confidences

    def rank_paths(self, seed_id: str, top_n: int = 10) -> List[Dict[str, Any]]:
        """Rank citation paths from the seed paper toward older papers.

        Only the best ``top_n`` paths are returned, so candidates are streamed
        through a bounded heap instead of being materialised. A densely
        interlinked topic can contain tens of thousands of simple paths, and
        building a result dict for every one of them (only to discard all but
        ten) dominated the runtime of a whole analysis.
        """
        if seed_id not in self.graph:
            return []

        best: List[tuple] = []  # min-heap of (score, tiebreak, path, weights, confs)
        tiebreak = 0
        examined = 0
        truncated = False

        for path in self._iter_paths(seed_id):
            examined += 1
            if examined > self.MAX_PATHS_EXAMINED:
                truncated = True
                break

            score, weights, confs = self._score_path(path)
            entry = (score, tiebreak, path, weights, confs)
            tiebreak += 1
            if len(best) < top_n:
                heapq.heappush(best, entry)
            elif score > best[0][0]:
                heapq.heapreplace(best, entry)

        if truncated:
            logger.warning(
                "Path search hit the %d-path cap; ranking the best of those examined.",
                self.MAX_PATHS_EXAMINED,
            )

        ranked_paths = []
        for rank, (score, _, path, weights, confs) in enumerate(
            sorted(best, key=lambda e: e[0], reverse=True), start=1
        ):
            ranked_paths.append({
                "rank": rank,
                "path": path,
                "score": score,
                "titles": [self.graph.nodes[n].get('title', n) for n in path],
                "paper_ids": path,
                "path_score": score,
                "edge_weights": weights,
                "average_confidence": sum(confs) / len(confs),
                "path_length": len(path) - 1,
                "explanation": "Citation path ranked by edge weight, edge confidence, and path depth."
            })
        return ranked_paths
