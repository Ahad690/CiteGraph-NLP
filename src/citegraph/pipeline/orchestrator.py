import uuid
import logging
from datetime import datetime
from typing import Optional

from citegraph.models.paper import PaperQuery
from citegraph.models.run import RunResult
from citegraph.input.normalizer import InputNormalizer
from citegraph.metadata.resolver import MetadataResolver
from citegraph.nlp.population_extractor import PopulationExtractor
from citegraph.nlp.population_resolver import PopulationResolver
from citegraph.citations.retriever import CitationRetriever
from citegraph.citations.traversal import CitationTraversal
from citegraph.graph.builder import GraphBuilder
from citegraph.graph.weighting import WeightCalculator
from citegraph.graph.analytics import GraphAnalytics
from citegraph.config import settings

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self):
        self.normalizer = InputNormalizer()
        self.metadata_resolver = MetadataResolver()
        self.pop_extractor = PopulationExtractor()
        self.pop_resolver = PopulationResolver()
        self.citation_retriever = CitationRetriever()
        self.weight_calc = WeightCalculator()
        self.graph_builder = GraphBuilder()

    async def run(self, query: PaperQuery, backward_depth: int = 2, forward_depth: int = 1, max_papers: int = 100) -> RunResult:
        run_id = str(uuid.uuid4())
        logger.info(f"Starting run {run_id} for {query.value}")

        # 1. Normalize input
        normalized_query = self.normalizer.normalize_query(query)

        # 2. Resolve seed paper
        seed_paper = await self.metadata_resolver.resolve_full(normalized_query)

        # 3. Traversal
        traversal = CitationTraversal(self.metadata_resolver, self.citation_retriever)
        await traversal.traverse(seed_paper, backward_depth, forward_depth, max_papers)

        # 4. Population Extraction for all papers
        all_candidates = []
        all_resolutions = []
        studies = []
        for paper_id, paper in traversal.papers.items():
            # Create a study node for each paper (simplified mapping)
            study_id = f"study_{paper_id}"
            study = Study(
                study_id=study_id,
                inferred=True,
                dedupe_confidence=0.8
            )
            studies.append(study)

            # In MVP, we might only have the abstract for extraction
            candidates = self.pop_extractor.extract_candidates(paper_id, paper.abstract or "", section="abstract")
            all_candidates.extend(candidates)
            
            res = self.pop_resolver.resolve(paper_id, candidates)
            res.study_id = study_id
            all_resolutions.append(res)

        # 5. Weighting
        weighted_edges = self.weight_calc.calculate_weights(traversal.edges, all_resolutions)

        # 6. Graph Building & Analytics
        graph = self.graph_builder.build(list(traversal.papers.values()), weighted_edges, all_resolutions)
        analytics = GraphAnalytics(graph)
        
        foundational_papers = analytics.rank_foundational_papers()
        ranked_paths = analytics.rank_paths(seed_paper.paper_id)

        return RunResult(
            run_id=run_id,
            seed_paper_id=seed_paper.paper_id,
            papers=list(traversal.papers.values()),
            studies=studies,
            population_candidates=all_candidates,
            population_resolutions=all_resolutions,
            citation_edges=weighted_edges,
            ranked_foundational_papers=foundational_papers,
            ranked_paths=ranked_paths,
            warnings=[],
            created_at=datetime.utcnow()
        )
