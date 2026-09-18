"""Manually annotated gold standard for population-extraction evaluation.

Annotation protocol
-------------------
Each record was labelled by reading the abstract text retrieved from OpenAlex
(falling back to Europe PMC), not from the title and not from memory. The
supporting sentence is quoted verbatim in ``evidence`` so every label is
auditable.

Label definition
    ``n_eff`` is the total number of human subjects the paper's primary
    analysis is based on, as stated in the abstract. When the abstract reports
    no human study population, ``n_eff`` is ``None``. A paper is then a true
    negative: the correct behaviour is to extract nothing.

Deliberate hard cases
    Several negatives contain large, salient numbers that are *not* study
    populations -- an epidemic case tally, an image-dataset size, a count of
    reviewed studies. They are included to measure false positives, which a
    positives-only set would hide.

Limitations (must be reported in any results that use this set)
    * Single annotator, who is also the system author; no inter-annotator
      agreement was measured.
    * 20 papers is small; interval estimates are wide.
    * Abstracts only. Sample sizes stated solely in a full-text Methods
      section are out of scope, which matches what the pipeline reads.
    * Biomedical-heavy, reflecting the intended domain; the non-clinical
      papers are present as negatives, not as a representative sample.
"""

from typing import Any, Optional

# (doi, n_eff, semantic_type, evidence sentence)
GOLD_POPULATION: list[dict[str, Any]] = [
    {
        "doi": "10.1056/nejmoa2034577",
        "n_eff": 43548,
        "semantic_type": "TOTAL_RANDOMIZED",
        "design": "rct",
        "evidence": "A total of 43,548 participants underwent randomization, of whom 43,448 received injections.",
    },
    {
        "doi": "10.1056/nejmoa2035389",
        "n_eff": 30420,
        "semantic_type": "TOTAL_ENROLLED",
        "design": "rct",
        "evidence": "The trial enrolled 30,420 volunteers who were randomly assigned in a 1:1 ratio.",
    },
    {
        "doi": "10.1056/nejmoa1911303",
        "n_eff": 4744,
        "semantic_type": "TOTAL_RANDOMIZED",
        "design": "rct",
        "evidence": "we randomly assigned 4744 patients with New York Heart Association class II, III, or IV heart failure",
    },
    {
        "doi": "10.1056/nejmoa1812389",
        "n_eff": 17160,
        "semantic_type": "TOTAL_ANALYZED",
        "design": "rct",
        "evidence": "We evaluated 17,160 patients, including 10,186 without atherosclerotic cardiovascular disease.",
    },
    {
        "doi": "10.1016/s0140-6736(20)31604-4",
        "n_eff": 1077,
        "semantic_type": "TOTAL_ENROLLED",
        "design": "rct",
        "evidence": "1077 participants were enrolled and assigned to receive either ChAdOx1 nCoV-19 (n=543) or MenACWY (n=534)",
    },
    {
        "doi": "10.1056/nejmoa2002032",
        "n_eff": 1099,
        "semantic_type": "TOTAL_ANALYZED",
        "design": "cohort",
        "evidence": "We extracted data regarding 1099 patients with laboratory-confirmed Covid-19 from 552 hospitals.",
    },
    {
        "doi": "10.1016/s0140-6736(20)30183-5",
        "n_eff": 41,
        "semantic_type": "TOTAL_ANALYZED",
        "design": "case_series",
        "evidence": "By Jan 2, 2020, 41 admitted hospital patients had been identified as having laboratory-confirmed 2019-nCoV infection.",
    },
    {
        "doi": "10.1001/jama.2020.1585",
        "n_eff": 138,
        "semantic_type": "TOTAL_ANALYZED",
        "design": "case_series",
        "evidence": "Retrospective, single-center case series of the 138 consecutive hospitalized patients with confirmed NCIP.",
    },
    {
        "doi": "10.1056/nejmoa2001316",
        "n_eff": 425,
        "semantic_type": "TOTAL_ANALYZED",
        "design": "epidemiological",
        "evidence": "We analyzed data on the first 425 confirmed cases in Wuhan.",
    },
    {
        "doi": "10.1016/s2213-2600(20)30079-5",
        "n_eff": 52,
        "semantic_type": "TOTAL_ENROLLED",
        "design": "cohort",
        "evidence": "we enrolled 52 critically ill adult patients with SARS-CoV-2 pneumonia.",
    },
    {
        "doi": "10.1016/s1473-3099(20)30243-7",
        "n_eff": 1334,
        "semantic_type": "SAMPLE_SIZE_GENERIC",
        "design": "modelling",
        "evidence": "We also estimated the case fatality ratio from individual line-list data on 1334 cases identified outside of mainland China.",
    },
    # ---- true negatives: no human study population in the abstract ----
    {
        "doi": "10.1056/nejmoa2001017",
        "n_eff": None,
        "semantic_type": None,
        "design": "virus_characterisation",
        "evidence": "Abstract describes isolation of a novel betacoronavirus; no study population size is stated.",
    },
    {
        "doi": "10.1038/s41586-020-2012-7",
        "n_eff": None,
        "semantic_type": None,
        "design": "virus_characterisation",
        "evidence": "HARD NEGATIVE: '2,794 laboratory-confirmed infections including 80 deaths' is an epidemic tally, not this study's sample.",
    },
    {
        "doi": "10.1136/bmj.m1328",
        "n_eff": None,
        "semantic_type": None,
        "design": "systematic_review",
        "evidence": "HARD NEGATIVE: a systematic review of prediction models; its units are studies, not patients.",
    },
    {
        "doi": "10.1038/s41577-020-0311-8",
        "n_eff": None,
        "semantic_type": None,
        "design": "review",
        "evidence": "Narrative review of COVID-19 immunology; no study population.",
    },
    {
        "doi": "10.1164/rccm.201908-1581st",
        "n_eff": None,
        "semantic_type": None,
        "design": "guideline",
        "evidence": "Clinical practice guideline; no study population.",
    },
    {
        "doi": "10.1056/nejmra2026131",
        "n_eff": None,
        "semantic_type": None,
        "design": "review",
        "evidence": "Review article on cytokine storm; no study population.",
    },
    {
        "doi": "10.1038/s41586-021-03819-2",
        "n_eff": None,
        "semantic_type": None,
        "design": "computational",
        "evidence": "HARD NEGATIVE: protein-structure prediction; CASP14 target counts are not human subjects.",
    },
    {
        "doi": "10.1038/nature14539",
        "n_eff": None,
        "semantic_type": None,
        "design": "review",
        "evidence": "Review of deep learning; no study population.",
    },
    {
        "doi": "10.1145/3065386",
        "n_eff": None,
        "semantic_type": None,
        "design": "computational",
        "evidence": "HARD NEGATIVE: '1.2 million high-resolution images' is a dataset size, not a human study population.",
    },
]


def positives() -> list[dict[str, Any]]:
    return [r for r in GOLD_POPULATION if r["n_eff"] is not None]


def negatives() -> list[dict[str, Any]]:
    return [r for r in GOLD_POPULATION if r["n_eff"] is None]


def by_doi(doi: str) -> Optional[dict[str, Any]]:
    doi = (doi or "").lower()
    return next((r for r in GOLD_POPULATION if r["doi"] == doi), None)
