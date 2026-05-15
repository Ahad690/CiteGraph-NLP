import networkx as nx
from typing import List, Dict, Any

class GraphAnalytics:
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph

    def rank_foundational_papers(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Rank papers by their 'foundational' score."""
        if not self.graph.nodes:
            return []

        # Simple ranking: PageRank or In-degree centrality weighted by edge weights
        # Foundational papers are usually older and have many incoming citations
        
        pagerank = nx.pagerank(self.graph, weight='weight')
        
        results = []
        for paper_id, score in pagerank.items():
            node_data = self.graph.nodes[paper_id]
            results.append({
                "paper_id": paper_id,
                "title": node_data.get("title"),
                "year": node_data.get("year"),
                "score": score,
                "n_eff": node_data.get("n_eff"),
                "explanation": f"Ranked foundational with PageRank score of {score:.4f}"
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
