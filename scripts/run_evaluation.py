"""Run the evaluation plan from the project proposal (Section 13).

Produces a JSON artifact plus a human-readable summary. Every number quoted in
the thesis must come from this script so it can be recomputed.

    python scripts/run_evaluation.py --out thesis/evidence
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from citegraph.evaluation.gold_standard import GOLD_POPULATION, positives, negatives
from citegraph.evaluation.metrics import (
    ClassificationScores,
    graph_connectivity,
    normalised_title_similarity,
    wilson_interval,
)
from citegraph.models.paper import PaperQuery
from citegraph.metadata.resolver import MetadataResolver
from citegraph.citations.retriever import CitationRetriever
from citegraph.citations.traversal import CitationTraversal
from citegraph.nlp.population_extractor import PopulationExtractor
from citegraph.nlp.population_resolver import PopulationResolver
from citegraph.providers.europe_pmc import EuropePMCProvider
from citegraph.providers.base import close_shared_client


async def fetch_abstracts(dois: list[str]) -> dict[str, dict]:
    """Resolve each gold DOI through the real pipeline path."""
    resolver = MetadataResolver()
    europe_pmc = EuropePMCProvider()
    papers: dict[str, dict] = {}

    for doi in dois:
        record = {"paper": None, "error": None, "abstract_source": None}
        try:
            paper = await resolver.resolve_full(PaperQuery(query_type="doi", value=doi))
            record["paper"] = paper
            record["abstract_source"] = "provider" if paper.abstract else None
        except Exception as e:  # noqa: BLE001
            record["error"] = str(e)
        papers[doi] = record

    # Same backfill the pipeline performs.
    missing = [d for d, r in papers.items() if r["paper"] is not None and not r["paper"].abstract]
    if missing:
        recovered = await europe_pmc.get_abstracts_by_doi(missing)
        for doi in missing:
            text = recovered.get(doi)
            if text:
                papers[doi]["paper"].abstract = text
                papers[doi]["abstract_source"] = "europepmc_backfill"
    return papers


def evaluate_population(papers: dict[str, dict]) -> dict:
    """Detection, value accuracy and semantic-type accuracy against the gold set."""
    extractor = PopulationExtractor()
    resolver = PopulationResolver()

    detection = ClassificationScores()
    value_correct = value_total = 0
    type_correct = type_total = 0
    per_paper = []
    confidence_when_right: list[float] = []
    confidence_when_wrong: list[float] = []

    for gold in GOLD_POPULATION:
        doi = gold["doi"]
        entry = papers.get(doi) or {}
        paper = entry.get("paper")
        abstract = (paper.abstract if paper else "") or ""

        candidates = extractor.extract_candidates(doi, abstract, section="abstract")
        resolution = resolver.resolve(doi, candidates)
        predicted = resolution.n_eff
        expected = gold["n_eff"]

        if expected is not None and predicted is not None:
            detection.true_positive += 1
        elif expected is not None and predicted is None:
            detection.false_negative += 1
        elif expected is None and predicted is not None:
            detection.false_positive += 1
        else:
            detection.true_negative += 1

        exact = None
        if expected is not None:
            value_total += 1
            exact = predicted == expected
            if exact:
                value_correct += 1
            if predicted is not None:
                (confidence_when_right if exact else confidence_when_wrong).append(resolution.confidence)
            if exact and gold["semantic_type"]:
                type_total += 1
                if resolution.semantic_type == gold["semantic_type"]:
                    type_correct += 1

        per_paper.append({
            "doi": doi,
            "design": gold["design"],
            "expected_n_eff": expected,
            "predicted_n_eff": predicted,
            "exact_value_match": exact,
            "expected_type": gold["semantic_type"],
            "predicted_type": resolution.semantic_type,
            "status": resolution.status,
            "confidence": round(resolution.confidence, 3),
            "candidates_found": len(candidates),
            "had_abstract": bool(abstract),
            "abstract_source": entry.get("abstract_source"),
        })

    def mean(xs):
        return round(sum(xs) / len(xs), 3) if xs else None

    return {
        "detection": detection.as_dict(),
        "detection_accuracy_ci95": wilson_interval(
            detection.true_positive + detection.true_negative, detection.support
        ),
        "value_exact_accuracy": (value_correct / value_total) if value_total else None,
        "value_exact_accuracy_ci95": wilson_interval(value_correct, value_total),
        "value_correct": value_correct,
        "value_total": value_total,
        "semantic_type_accuracy": (type_correct / type_total) if type_total else None,
        "semantic_type_correct": type_correct,
        "semantic_type_total": type_total,
        "mean_confidence_when_value_correct": mean(confidence_when_right),
        "mean_confidence_when_value_wrong": mean(confidence_when_wrong),
        "per_paper": per_paper,
    }


def evaluate_metadata(papers: dict[str, dict]) -> dict:
    """Resolution success and field completeness against the gold DOIs."""
    resolved = [r for r in papers.values() if r["paper"] is not None]
    total = len(papers)
    doi_exact = sum(
        1 for doi, r in papers.items()
        if r["paper"] is not None and (r["paper"].doi or "").lower() == doi.lower()
    )
    have_title = sum(1 for r in resolved if r["paper"].title and r["paper"].title != "Unknown Title")
    have_year = sum(1 for r in resolved if r["paper"].year)
    have_journal = sum(1 for r in resolved if r["paper"].journal)
    have_authors = sum(1 for r in resolved if r["paper"].authors)
    have_abstract = sum(1 for r in resolved if r["paper"].abstract)
    backfilled = sum(1 for r in papers.values() if r["abstract_source"] == "europepmc_backfill")

    return {
        "papers_attempted": total,
        "papers_resolved": len(resolved),
        "resolution_rate": len(resolved) / total if total else None,
        "doi_exact_match": doi_exact,
        "doi_exact_match_rate": doi_exact / total if total else None,
        "field_completeness": {
            "title": have_title / len(resolved) if resolved else None,
            "year": have_year / len(resolved) if resolved else None,
            "journal": have_journal / len(resolved) if resolved else None,
            "authors": have_authors / len(resolved) if resolved else None,
            "abstract": have_abstract / len(resolved) if resolved else None,
        },
        "abstracts_backfilled_from_europepmc": backfilled,
    }


async def evaluate_graph(seed_dois: list[str], max_papers: int) -> dict:
    """Structural quality and cost of real traversals."""
    resolver = MetadataResolver()
    retriever = CitationRetriever()
    runs = []

    for doi in seed_dois:
        started = time.time()
        try:
            seed = await resolver.resolve_full(PaperQuery(query_type="doi", value=doi))
            traversal = CitationTraversal(resolver, retriever)
            await traversal.traverse(seed, 2, 1, max_papers)
        except Exception as e:  # noqa: BLE001
            runs.append({"seed_doi": doi, "error": str(e)})
            continue

        elapsed = time.time() - started
        stats = graph_connectivity(list(traversal.papers.keys()), traversal.edges)
        backward = sum(1 for e in traversal.edges if e.source_paper_id == seed.paper_id)
        forward = sum(1 for e in traversal.edges if e.target_paper_id == seed.paper_id)
        runs.append({
            "seed_doi": doi,
            "seed_title": seed.title,
            "requested_max_papers": max_papers,
            "elapsed_seconds": round(elapsed, 1),
            "seed_backward_edges": backward,
            "seed_forward_edges": forward,
            "duplicates_merged": traversal.duplicates_merged,
            **stats,
        })

    completed = [r for r in runs if "error" not in r]
    return {
        "runs": runs,
        "aggregate": {
            "runs_completed": len(completed),
            "total_dangling_edges": sum(r["dangling_edges"] for r in completed),
            "total_isolated_nodes": sum(r["isolated_nodes"] for r in completed),
            "total_duplicates_merged": sum(r["duplicates_merged"] for r in completed),
            "mean_elapsed_seconds": round(
                sum(r["elapsed_seconds"] for r in completed) / len(completed), 1
            ) if completed else None,
            "mean_connected_fraction": round(
                sum(r["connected_fraction"] for r in completed) / len(completed), 4
            ) if completed else None,
        },
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="thesis/evidence")
    parser.add_argument("--max-papers", type=int, default=40)
    parser.add_argument("--skip-graph", action="store_true")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    dois = [r["doi"] for r in GOLD_POPULATION]
    print(f"Resolving {len(dois)} gold-standard papers ...")
    papers = await fetch_abstracts(dois)

    print("Evaluating metadata resolution ...")
    metadata = evaluate_metadata(papers)

    print("Evaluating population extraction ...")
    population = evaluate_population(papers)

    graph = {"skipped": True}
    if not args.skip_graph:
        seeds = [
            "10.1056/NEJMoa2002032",
            "10.1038/s41586-021-03819-2",
            "10.1056/NEJMoa1911303",
        ]
        print(f"Running {len(seeds)} traversals at max_papers={args.max_papers} ...")
        graph = await evaluate_graph(seeds, args.max_papers)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gold_standard_size": len(GOLD_POPULATION),
        "gold_positives": len(positives()),
        "gold_negatives": len(negatives()),
        "metadata": metadata,
        "population_extraction": population,
        "citation_graph": graph,
    }

    path = os.path.join(args.out, "evaluation_results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    d = population["detection"]
    print(f"\n--- population extraction (n={len(GOLD_POPULATION)}) ---")
    print(f"  detection   TP={d['true_positive']} FP={d['false_positive']} "
          f"TN={d['true_negative']} FN={d['false_negative']}")
    print(f"  precision   {d['precision']}")
    print(f"  recall      {d['recall']}")
    print(f"  specificity {d['specificity']}")
    print(f"  F1          {d['f1']}")
    print(f"  value exact {population['value_correct']}/{population['value_total']}")
    print(f"  type acc    {population['semantic_type_correct']}/{population['semantic_type_total']}")
    print(f"\n--- metadata ---")
    print(f"  resolved {metadata['papers_resolved']}/{metadata['papers_attempted']}, "
          f"abstracts backfilled {metadata['abstracts_backfilled_from_europepmc']}")
    if not graph.get("skipped"):
        print(f"\n--- graph ---")
        print(f"  {graph['aggregate']}")
    print(f"\nwritten -> {path}")

    await close_shared_client()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
