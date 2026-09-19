from citegraph.metadata.merger import MetadataMerger
from citegraph.models.paper import Paper
from citegraph.nlp.technical_evidence import TechnicalEvidenceExtractor
from citegraph.providers.base import ProviderResult
from citegraph.providers.openalex import OpenAlexProvider
from citegraph.pipeline.orchestrator import PipelineOrchestrator
from citegraph.citations.traversal import CitationTraversal
from citegraph.models.paper import PaperQuery
from citegraph.models.citation import CitationEdge
from datetime import datetime, timezone
import fitz

from citegraph.providers.arxiv_full_text import ArxivFullTextProvider


def test_openalex_field_classifies_computer_science():
    provider = OpenAlexProvider()
    paper = provider._map_to_paper({
        "id": "https://openalex.org/W1234567890",
        "doi": "https://doi.org/10.1234/technical",
        "display_name": "A transformer model",
        "primary_topic": {"field": {"display_name": "Computer Science"}, "domain": {"display_name": "Physical Sciences"}},
    })
    assert paper.research_domain == "computer_science"
    merged = MetadataMerger().merge({"openalex": ProviderResult(paper=paper)})
    assert merged.research_domain == "computer_science"


def test_openalex_identifies_linked_arxiv_pdf():
    paper = OpenAlexProvider()._map_to_paper({
        "id": "https://openalex.org/W1234567890",
        "display_name": "Attention Is All You Need",
        "primary_topic": {"field": {"display_name": "Computer Science"}},
        "locations": [{"landing_page_url": "http://arxiv.org/abs/1706.03762", "pdf_url": "https://arxiv.org/pdf/1706.03762"}],
    })
    assert paper.arxiv_id == "1706.03762"


async def test_arxiv_pdf_reads_dataset_section_without_references(respx_mock):
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "5.1 Training Data and Batching\nWe trained on 4.5 million sentence pairs.\nReferences\nOther work used 9 million examples.")
    pdf = document.tobytes()
    document.close()
    respx_mock.get("https://arxiv.org/pdf/1706.03762").respond(content=pdf)

    text = await ArxivFullTextProvider().get_dataset_sections("1706.03762")

    assert text is not None
    assert "4.5 million sentence pairs" in text
    assert "9 million examples" not in text


def test_physical_science_is_not_a_clinical_population():
    paper = OpenAlexProvider()._map_to_paper({
        "id": "https://openalex.org/W1234567891",
        "display_name": "Quantum processor",
        "primary_topic": {"field": {"display_name": "Physics and Astronomy"}, "domain": {"display_name": "Physical Sciences"}},
    })
    assert paper.research_domain == "nonclinical"


def test_quantum_hardware_is_not_treated_as_dataset_research():
    paper = OpenAlexProvider()._map_to_paper({
        "id": "https://openalex.org/W7129804874",
        "display_name": "Fully integrated quantum frequency processor on a silicon chip",
        "primary_topic": {
            "display_name": "Quantum Information and Cryptography",
            "field": {"display_name": "Computer Science"},
            "domain": {"display_name": "Physical Sciences"},
        },
    })
    assert paper.research_domain == "nonclinical"


def test_technical_extractor_finds_explicit_training_examples():
    evidence = TechnicalEvidenceExtractor().extract(
        "paper-1", "We trained the model on 4.5 million sentence pairs. The model has 65 million parameters."
    )
    assert evidence.status == "resolved"
    assert evidence.kind == "training_examples"
    assert evidence.value == 4_500_000
    assert evidence.unit == "sentence pairs"
    assert "sentence pairs" in evidence.evidence


def test_technical_extractor_does_not_invent_dataset_size():
    evidence = TechnicalEvidenceExtractor().extract(
        "paper-2", "Our model has 65 million parameters and outperforms earlier systems."
    )
    assert evidence.status == "missing"
    assert evidence.value is None


def test_different_training_counts_are_marked_ambiguous():
    evidence = TechnicalEvidenceExtractor().extract(
        "paper-3", "We trained on 50,000 images. A second training dataset contains 120,000 images."
    )
    assert evidence.status == "ambiguous"
    assert evidence.value == 120_000


def test_training_count_takes_priority_over_test_count_in_same_sentence():
    evidence = TechnicalEvidenceExtractor().extract(
        "paper-4", "We trained on 50,000 examples and tested on 10,000 examples."
    )
    assert evidence.kind == "training_examples"
    assert evidence.value == 50_000


async def test_pipeline_keeps_technical_evidence_out_of_clinical_population(monkeypatch):
    paper = Paper(
        paper_id="technical-paper",
        title="A transformer model",
        abstract="We trained on 4.5 million sentence pairs.",
        research_domain="computer_science",
    )
    clinical_paper = Paper(
        paper_id="clinical-reference", title="Clinical trial",
        abstract="We enrolled 1,000 patients.", research_domain="biomedical",
    )
    pipeline = PipelineOrchestrator()

    async def resolve_full(query):
        return paper

    async def traverse(self, seed, backward_depth, forward_depth, max_papers):
        self.papers = {seed.paper_id: seed, clinical_paper.paper_id: clinical_paper}
        self.edges = [CitationEdge(
            edge_id="edge-1", source_paper_id=seed.paper_id, target_paper_id=clinical_paper.paper_id,
            providers=["openalex"], confidence=1.0, retrieved_at=datetime.now(timezone.utc),
        )]

    monkeypatch.setattr(pipeline.metadata_resolver, "resolve_full", resolve_full)
    monkeypatch.setattr(CitationTraversal, "traverse", traverse)
    result = await pipeline.run(PaperQuery(query_type="title", value=paper.title))

    assert result.population_resolutions[0].status == "not_applicable"
    assert result.population_resolutions[0].n_eff is None
    assert result.population_resolutions[1].n_eff == 1000
    assert result.technical_evidence[0].value == 4_500_000
    assert result.citation_edges[0].n_score == 0
    assert result.citation_edges[0].final_weight == 0.125
    assert all(item["n_eff"] == 0 for item in result.ranked_foundational_papers)


async def test_pipeline_uses_arxiv_only_after_abstract_misses(monkeypatch):
    paper = Paper(
        paper_id="arxiv-paper", title="Translation model",
        research_domain="computer_science", arxiv_id="1706.03762",
        abstract="A model for translation without an explicit dataset count.",
    )
    pipeline = PipelineOrchestrator()
    calls = []

    async def get_sections(arxiv_id):
        calls.append(arxiv_id)
        return "Training Data and Batching. We trained on 4.5 million sentence pairs."

    monkeypatch.setattr(pipeline.arxiv_full_text, "get_dataset_sections", get_sections)
    evidence = [pipeline.technical_extractor.extract(paper.paper_id, paper.abstract)]
    recovered = await pipeline._recover_technical_from_full_text({paper.paper_id: paper}, evidence, paper.paper_id)

    assert recovered == 1
    assert calls == ["1706.03762"]
    assert evidence[0].value == 4_500_000
    assert evidence[0].section == "full_text"
    assert paper.provenance["technical_full_text"]["arxiv_id"] == "1706.03762"
