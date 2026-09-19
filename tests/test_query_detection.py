"""Identifier auto-detection, and the title matching that follows it.

These cover the two defects behind run ac66eb9e: an IEEE URL and a paper title
were both handed straight to OpenAlex's /works/{id} endpoint, which 404s for
anything that is not an identifier.
"""

import pytest

from citegraph.models.paper import PaperQuery
from citegraph.providers.base import (
    MIN_TITLE_MATCH,
    _best_title_match,
    title_similarity,
)
from citegraph.utils.ids import IdCanonicalizer, detect_query_type


class TestDetectQueryType:
    @pytest.mark.parametrize("value,expected", [
        # DOIs, bare and prefixed
        ("10.1056/NEJMoa2001017", "doi"),
        ("doi:10.1056/NEJMoa2001017", "doi"),
        ("10.1016/S0169-7552(98)00110-X", "doi"),
        # A URL wins over the DOI inside it, so the URL resolver can strip
        # publisher view segments such as /full before lookup.
        ("https://doi.org/10.1056/NEJMoa2001017", "url"),
        ("https://ieeexplore.ieee.org/document/4812104", "url"),
        ("http://example.org/article", "url"),
        ("www.nature.com/articles/s41586", "url"),
        # PubMed Central
        ("PMC13130204", "pmcid"),
        ("PMCID: PMC8012345", "pmcid"),
        # PubMed
        ("42059664", "pmid"),
        ("PMID: 34567890", "pmid"),
        # OpenAlex work ids go down the providers' DOI path
        ("W2003241", "doi"),
        # Anything else is free text
        ("Attention Is All You Need", "title"),
        ("SARS-CoV-2 transmission dynamics", "title"),
        ("10.1234", "title"),          # a DOI prefix with no suffix is not a DOI
        ("", "title"),
        ("   ", "title"),
    ])
    def test_detects(self, value, expected):
        assert detect_query_type(value) == expected

    def test_paper_query_resolves_auto_at_construction(self):
        """Nothing downstream of the model should ever see query_type "auto"."""
        assert PaperQuery(value="10.1056/NEJMoa2001017").query_type == "doi"
        assert PaperQuery(value="Attention Is All You Need").query_type == "title"
        assert PaperQuery(query_type="auto", value="PMC8012345").query_type == "pmcid"

    def test_explicit_type_is_not_overridden(self):
        """A caller who states a type keeps it, even if detection disagrees."""
        query = PaperQuery(query_type="title", value="10.1056/NEJMoa2001017")
        assert query.query_type == "title"


class TestOpenAlexIdFormatting:
    @pytest.mark.parametrize("value", [
        "Attention Is All You Need",
        "https://ieeexplore.ieee.org/document/4812104",
        "not an identifier at all",
        "",
    ])
    def test_non_identifiers_produce_no_openalex_id(self, value):
        """The fall-through that made GET /works/{title} possible is gone.

        Returning the input unchanged meant a title became a path segment and
        OpenAlex answered 404, so it contributed nothing to a title search
        while appearing in the logs as a provider failure.
        """
        assert IdCanonicalizer.to_openalex_id(value) == ""

    @pytest.mark.parametrize("value,expected", [
        ("10.1056/NEJMoa2001017", "doi:10.1056/nejmoa2001017"),
        ("PMC8012345", "pmcid:PMC8012345"),
        ("34567890", "pmid:34567890"),
        ("W2003241", "W2003241"),
    ])
    def test_real_identifiers_still_format(self, value, expected):
        assert IdCanonicalizer.to_openalex_id(value) == expected


class TestTitleMatching:
    def test_identical_titles_score_one(self):
        assert title_similarity("Attention Is All You Need",
                                "attention is all you need") == 1.0

    def test_unrelated_titles_score_low(self):
        assert title_similarity("Attention Is All You Need",
                                "Deep Residual Learning") < 0.2

    def test_a_longer_variant_does_not_pass_as_the_same_paper(self):
        """"Channel Attention Is All You Need for Video" is a different paper."""
        score = title_similarity(
            "Attention Is All You Need",
            "Channel Attention Is All You Need for Video Classification",
        )
        assert score < MIN_TITLE_MATCH

    def test_picks_the_best_match_not_the_first(self):
        candidates = [
            {"title": "Is Attention All You Need? A Survey", "cited_by_count": 900},
            {"title": "Attention Is All You Need", "cited_by_count": 10},
        ]
        best, score = _best_title_match(
            "Attention Is All You Need", candidates, lambda c: c["title"],
            cited_by=lambda c: c["cited_by_count"],
        )
        assert best["title"] == "Attention Is All You Need"
        assert score == 1.0

    def test_citation_count_breaks_ties_between_duplicates(self):
        """Mirror records share a title; prefer the one the literature cites.

        Searching a famous title returns a cluster of identical-titled
        duplicates, and the provider's own ranking does not reliably put the
        real one first.
        """
        candidates = [
            {"title": "Attention Is All You Need", "cited_by_count": 3},
            {"title": "Attention Is All You Need", "cited_by_count": 7566},
            {"title": "Attention Is All You Need", "cited_by_count": 11},
        ]
        best, _ = _best_title_match(
            "Attention Is All You Need", candidates, lambda c: c["title"],
            cited_by=lambda c: c["cited_by_count"],
        )
        assert best["cited_by_count"] == 7566

    def test_returns_nothing_when_no_candidate_is_close_enough(self):
        candidates = [{"title": "An entirely different paper", "cited_by_count": 5}]
        best, score = _best_title_match(
            "Attention Is All You Need", candidates, lambda c: c["title"],
            cited_by=lambda c: c["cited_by_count"],
        )
        assert best is None
        assert score == 0.0

    def test_missing_citation_counts_do_not_raise(self):
        candidates = [{"title": "Attention Is All You Need", "cited_by_count": None}]
        best, _ = _best_title_match(
            "Attention Is All You Need", candidates, lambda c: c["title"],
            cited_by=lambda c: c["cited_by_count"],
        )
        assert best is not None
