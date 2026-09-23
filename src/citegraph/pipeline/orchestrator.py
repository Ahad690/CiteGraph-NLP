import uuid
import logging
import asyncio
import re
from datetime import datetime
from typing import Optional

from citegraph.models.paper import PaperQuery, Paper
from citegraph.models.study import Study
from citegraph.models.run import RunResult
from citegraph.input.normalizer import InputNormalizer
from citegraph.metadata.resolver import MetadataResolver, doi_is_dead
from citegraph.nlp.population_extractor import PopulationExtractor
from citegraph.nlp.population_resolver import PopulationResolver
from citegraph.nlp.technical_evidence import TechnicalEvidenceExtractor
from citegraph.models.population import PopulationResolution
from citegraph.models.technical_evidence import TechnicalEvidence
from citegraph.citations.retriever import CitationRetriever
from citegraph.providers.europe_pmc import EuropePMCProvider
from citegraph.providers.arxiv_full_text import ArxivFullTextProvider
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
        self.technical_extractor = TechnicalEvidenceExtractor()
        self.citation_retriever = CitationRetriever()
        self.europe_pmc = EuropePMCProvider()
        self.arxiv_full_text = ArxivFullTextProvider()
        self.weight_calc = WeightCalculator()
        self.graph_builder = GraphBuilder()

    async def _backfill_abstracts(self, papers: dict) -> int:
        """Fill in abstracts Europe PMC has but OpenAlex does not.

        Returns the number recovered. One batched search covers the whole set,
        so this is a single extra request for a typical run.
        """
        if not settings.enable_europe_pmc:
            return 0

        needing = [p for p in papers.values() if not p.abstract and p.doi]
        if not needing:
            return 0

        try:
            found = await self.europe_pmc.get_abstracts_by_doi([p.doi for p in needing])
        except Exception as e:
            logger.warning("Abstract backfill failed: %s", e)
            return 0

        recovered = 0
        for paper in needing:
            text = found.get(paper.doi)
            if text:
                paper.abstract = text
                paper.provenance.setdefault("europe_pmc", {})["abstract_backfilled"] = True
                recovered += 1
        if recovered:
            logger.info(
                "Backfilled %d abstract(s) from Europe PMC for %d paper(s) without one",
                recovered, len(needing),
            )
        return recovered

    async def _recover_from_full_text(self, papers: dict, resolutions: list) -> tuple[list, int]:
        missing = [papers[resolution.paper_id] for resolution in resolutions if resolution.status == "missing"]
        if not missing or not settings.enable_europe_pmc:
            return [], 0

        doi_to_pmcid = await self.europe_pmc.find_open_access_pmcids_by_doi(
            [paper.doi for paper in missing if paper.doi and not paper.pmcid]
        )
        semaphore = asyncio.Semaphore(5)

        async def recover(paper: Paper):
            pmcid = paper.pmcid or doi_to_pmcid.get(paper.doi or "")
            if not pmcid:
                return None
            async with semaphore:
                sections = await self.europe_pmc.get_full_text_sections(pmcid)
            candidates = []
            total_chars = 0
            for section, paragraph in sections:
                if total_chars + len(paragraph) > 250_000:
                    break
                total_chars += len(paragraph)
                for candidate in self.pop_extractor.extract_candidates(paper.paper_id, paragraph, section=section):
                    if re.search(
                        r"\b(patients?|participants?|subjects?|individuals?|volunteers?|cases?|cohort|population|sample size|randomiz\w*|enroll\w*|screen\w*|recruit\w*|followed|adults?|children|infants?|women|men)\b",
                        candidate.sentence,
                        re.IGNORECASE,
                    ):
                        candidates.append(candidate)
            recovered = self.pop_resolver.resolve(paper.paper_id, candidates)
            if recovered.status == "missing":
                return None
            paper.provenance["population_full_text"] = {"provider": "europe_pmc", "pmcid": pmcid}
            return paper.paper_id, candidates, recovered

        results = await asyncio.gather(*(recover(paper) for paper in missing))
        by_paper = {item[0]: item for item in results if item is not None}
        for resolution_index, resolution in enumerate(resolutions):
            replacement = by_paper.get(resolution.paper_id)
            if replacement:
                replacement[2].study_id = resolution.study_id
                resolutions[resolution_index] = replacement[2]
        return [candidate for item in by_paper.values() for candidate in item[1]], len(by_paper)

    async def recover_technical_from_full_text(self, paper: Paper) -> TechnicalEvidence | None:
        """Read one computer-science paper's arXiv PDF for dataset counts.

        Called when a user opens the paper, not during the run. arXiv asks for
        one request every three seconds, so fetching up to ten PDFs inside the
        run cost about 27 seconds, half of a typical computer-science run, and
        what it found is only displayed: dataset counts feed no ranking and no
        edge weight. Doing it for the one paper someone is looking at costs a
        few seconds for that paper and nothing for everyone else.

        Returns the recovered evidence, or None when the paper has no arXiv
        PDF or the PDF states no dataset count.
        """
        if not paper.arxiv_id:
            return None
        body = await self.arxiv_full_text.get_dataset_sections(paper.arxiv_id)
        if not body:
            return None
        recovered = self.technical_extractor.extract(paper.paper_id, body, section="full_text")
        if recovered.status == "missing":
            return None
        return recovered

    async def run(self, query: PaperQuery, backward_depth: int = 2, forward_depth: int = 1, max_papers: int = 100, run_id: str = None) -> RunResult:
        run_id = run_id or str(uuid.uuid4())
        logger.info(f"Starting run {run_id} for {query.value}")

        # 1. Normalize input
        normalized_query = self.normalizer.normalize_query(query)

        # 2. Resolve seed paper
        seed_paper = await self.metadata_resolver.resolve_full(normalized_query)

        # 3. Traversal
        traversal = CitationTraversal(self.metadata_resolver, self.citation_retriever)
        await traversal.traverse(seed_paper, backward_depth, forward_depth, max_papers)

        # 3b. Backfill abstracts. Population evidence can only be extracted from
        # text, and OpenAlex carries no abstract for a sizeable share of works,
        # so those papers would report "missing" purely for lack of input.
        abstracts_recovered = await self._backfill_abstracts(traversal.papers)

        # 4. Population Extraction for all papers
        all_candidates = []
        all_resolutions = []
        technical_evidence = []
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

            if paper.research_domain in ("computer_science", "nonclinical"):
                all_resolutions.append(PopulationResolution(
                    paper_id=paper_id,
                    study_id=study_id,
                    confidence=0.0,
                    status="not_applicable",
                    explanation="Clinical population size is not applicable to this research field.",
                ))
                if paper.research_domain == "computer_science":
                    technical_evidence.append(self.technical_extractor.extract(paper_id, paper.abstract))
                continue

            candidates = self.pop_extractor.extract_candidates(paper_id, paper.abstract or "", section="abstract")
            all_candidates.extend(candidates)
            
            res = self.pop_resolver.resolve(paper_id, candidates)
            res.study_id = study_id
            all_resolutions.append(res)

        # Clinical full-text recovery stays in the run because what it finds
        # changes edge weights and rankings. Computer-science dataset counts are
        # display-only, so their arXiv lookup happens when a user opens the
        # paper (recover_technical_from_full_text). The seed link check runs
        # alongside rather than after.
        (full_text_candidates, full_text_recovered), seed_doi_dead = await asyncio.gather(
            self._recover_from_full_text(traversal.papers, all_resolutions),
            doi_is_dead(seed_paper.doi),
        )
        all_candidates.extend(full_text_candidates)

        # 5. Weighting
        ranking_resolutions = all_resolutions if seed_paper.research_domain not in ("computer_science", "nonclinical") else []
        weighted_edges = self.weight_calc.calculate_weights(traversal.edges, ranking_resolutions)

        # 6. Graph Building & Analytics
        graph = self.graph_builder.build(list(traversal.papers.values()), weighted_edges, ranking_resolutions)
        analytics = GraphAnalytics(graph)
        
        foundational_papers = analytics.rank_foundational_papers()
        ranked_paths = analytics.rank_paths(seed_paper.paper_id)

        # Surface what the traversal had to work around, so a sparse graph can
        # be explained (few citations vs. records merged vs. lookups that failed).
        warnings = list(traversal.warnings)
        # Anything the seed resolution wanted to say: a title that matched
        # weakly, or providers that disagreed about which paper it meant.
        warnings.extend(getattr(self.metadata_resolver, "warnings", []))
        if seed_doi_dead:
            warnings.append(
                f"The seed paper's DOI ({seed_paper.doi}) is registered but its "
                "landing page returns 404. The metadata is real; the link is "
                "broken at the publisher. This happens with mirror and preprint "
                "records that duplicate a well-known title."
            )
            # Also recorded on the paper, so the dashboard can mark the link
            # itself. A warning on the overview page is easy to miss while the
            # paper drawer shows the same DOI with a working-looking open button.
            stored_seed = traversal.papers.get(seed_paper.paper_id, seed_paper)
            stored_seed.provenance["doi_link"] = {
                "status": "not_found",
                "checked_at": datetime.utcnow().isoformat(),
            }
        without_text = sum(1 for p in traversal.papers.values() if not p.abstract)
        if abstracts_recovered:
            warnings.append(
                f"Recovered {abstracts_recovered} abstract(s) from Europe PMC that "
                "OpenAlex did not carry; population evidence needs abstract text."
            )
        if full_text_recovered:
            warnings.append(
                f"Recovered population evidence for {full_text_recovered} paper(s) from "
                "Europe PMC open-access Methods/Results full text after abstract extraction found none."
            )
        if technical_evidence:
            warnings.append(
                "Computer-science dataset counts come from abstracts. Open a paper to read its "
                "arXiv PDF for a count the abstract does not state. They are not treated as "
                "clinical populations or used to weight citation rankings."
            )
        if without_text:
            warnings.append(
                f"{without_text} of {len(traversal.papers)} paper(s) have no abstract "
                "in any provider; open-access full text was tried where available."
            )
        if traversal.duplicates_merged:
            warnings.append(
                f"Merged {traversal.duplicates_merged} duplicate record(s): the same "
                "work was indexed under more than one identifier. Merging happens "
                "before the paper limit is applied, so it does not reduce the graph size."
            )

        return RunResult(
            run_id=run_id,
            seed_paper_id=seed_paper.paper_id,
            papers=list(traversal.papers.values()),
            studies=studies,
            population_candidates=all_candidates,
            population_resolutions=all_resolutions,
            technical_evidence=technical_evidence,
            citation_edges=weighted_edges,
            ranked_foundational_papers=foundational_papers,
            ranked_paths=ranked_paths,
            warnings=warnings,
            created_at=datetime.utcnow()
        )
