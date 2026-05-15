import networkx as nx
from typing import List, Dict
from citegraph.models.paper import Paper
from citegraph.models.citation import CitationEdge
from citegraph.models.population import PopulationResolution

class GraphBuilder:
    def build(self, papers: List[Paper], edges: List[CitationEdge], resolutions: List[PopulationResolution]) -> nx.DiGraph:
        """Build a NetworkX graph from papers, edges, and population resolutions."""
        graph = nx.DiGraph()
        res_map = {r.paper_id: r for r in resolutions}
        
        # Add nodes
        for paper in papers:
            res = res_map.get(paper.paper_id)
            graph.add_node(
                paper.paper_id,
                title=paper.title,
                year=paper.year,
                authors=", ".join(paper.authors[:3]) + ("..." if len(paper.authors) > 3 else ""),
                journal=paper.journal,
                n_eff=res.n_eff if res else None,
                population_confidence=res.confidence if res else 0.0,
                type="paper"
            )

        # Add edges
        for edge in edges:
            graph.add_edge(
                edge.source_paper_id,
                edge.target_paper_id,
                relation=edge.relation,
                confidence=edge.confidence,
                weight=edge.final_weight or 1.0,
                providers=",".join(edge.providers)
            )

        return graph
