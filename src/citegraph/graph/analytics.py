import networkx as nx
from typing import List, Dict, Any
import math

class GraphAnalytics:
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph

    def rank_foundational_papers(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Rank papers by their 'foundational' score using citation influence and evidence strength."""
        if not self.graph.nodes:
            return []

        # PageRank provides citation influence
        pagerank = nx.pagerank(self.graph, weight='weight')
        
        # Calculate a combined score
        # Foundational papers are:
        # 1. Heavily cited (PageRank)
        # 2. Older (Year bonus)
        # 3. High evidence quality (N_eff and confidence)
        
        current_year = 2026 # For demo purposes
        
        results = []
        for paper_id, influence_score in pagerank.items():
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
            
            results.append({
                "paper_id": paper_id,
                "title": node_data.get("title"),
                "year": year,
                "score": final_score,
                "influence": influence_score,
                "n_eff": n_eff,
                "explanation": f"Ranked foundational based on citation influence ({influence_score:.2f}), year ({year}), and evidence strength."
            })
            
        return sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]

    def rank_paths(self, seed_id: str, top_n: int = 10) -> List[Dict[str, Any]]:
        """Rank citation paths from seed paper to older papers."""
        if seed_id not in self.graph:
            return []

        # Find all paths from seed to nodes with no outgoing edges (leaf nodes/foundational)
        # Or just all paths of length > 1
        all_paths = []
        for node in self.graph.nodes:
            if node == seed_id:
                continue
            
            # Find all simple paths
            try:
                paths = list(nx.all_simple_paths(self.graph, seed_id, node, cutoff=4))
                all_paths.extend(paths)
            except nx.NetworkXNoPath:
                continue

        ranked_paths = []
        for path in all_paths:
            # path_score = average(final_edge_weight) * path_confidence * depth_bonus
            edge_weights = []
            edge_confidences = []
            
            for i in range(len(path) - 1):
                edge_data = self.graph.get_edge_data(path[i], path[i+1])
                edge_weights.append(edge_data.get('weight', 1.0))
                edge_confidences.append(edge_data.get('confidence', 1.0))

            avg_weight = sum(edge_weights) / len(edge_weights)
            path_confidence = 1.0
            for c in edge_confidences:
                path_confidence *= c
                
            depth_bonus = 1.0 / (len(path) ** 0.5)
            path_score = avg_weight * path_confidence * depth_bonus
            
            ranked_paths.append({
                "path": path,
                "score": path_score,
                "titles": [self.graph.nodes[node].get('title', node) for node in path]
            })

        return sorted(ranked_paths, key=lambda x: x["score"], reverse=True)[:top_n]
