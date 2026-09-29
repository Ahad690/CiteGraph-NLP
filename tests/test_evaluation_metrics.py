"""Tests for the metric functions the thesis quotes.

These four functions were at 0% coverage while `scripts/run_evaluation.py` used
them to produce the confidence intervals and detection-accuracy figures printed in
Chapter 6. That is the worst possible combination: numbers that are published
depend on code that nothing exercised. A Wilson interval is exactly the kind of
function that is wrong by a small amount and nobody notices, because the result
still looks like a plausible proportion.

The hand-computed interval at n=10, k=6 is the load-bearing case. It is the
thesis's own worked example -- 6 of 10 correct -- so a regression here would move
a published number rather than merely break a test.

Values are checked against the published Wilson score formula computed
independently here, not against a copy of the implementation, so the test cannot
pass by agreeing with a shared bug.
"""
from __future__ import annotations

import math

import pytest

from citegraph.evaluation.metrics import (
    ClassificationScores,
    exact_match_rate,
    graph_connectivity,
    normalised_title_similarity,
    wilson_interval,
)


def reference_wilson(successes: int, trials: int, z: float = 1.96) -> tuple:
    """The Wilson score interval, solved from its defining equation.

    The interval is the set of proportions p satisfying

        |p_hat - p| <= z * sqrt(p(1 - p) / n)

    Squaring both sides and collecting p gives

        (n + z^2) p^2 - (2 n p_hat + z^2) p + n p_hat^2 = 0

    whose two roots are the interval's endpoints. This is a different derivation
    from the closed form the implementation uses, so the two can only agree by
    both being right.

    An earlier version of this helper bisected the defining inequality instead,
    and got the boundary wrong: it reported an upper bound of exactly 0.5 for
    (0, 5) where the correct value is 0.4345. Two failures in a row -- the second
    from the test's own reference rather than the code under test -- is the
    argument for deriving the expected value independently.
    """
    phat = successes / trials
    a = trials + z * z
    b = -(2 * trials * phat + z * z)
    c = trials * phat * phat
    disc = b * b - 4 * a * c
    if disc < 0:
        raise AssertionError("Wilson discriminant went negative; inputs invalid")
    root = math.sqrt(disc)
    lo = (-b - root) / (2 * a)
    hi = (-b + root) / (2 * a)
    return (max(0.0, min(lo, hi)), min(1.0, max(lo, hi)))


class TestWilsonInterval:
    def test_the_thesis_worked_example(self):
        """6 of 10 is the case the thesis reports at 60%."""
        low, high = wilson_interval(6, 10)
        ref_low, ref_high = reference_wilson(6, 10)
        assert low == pytest.approx(ref_low, abs=1e-6)
        assert high == pytest.approx(ref_high, abs=1e-6)
        # The published interval for this case. Pinned as a literal as well as
        # checked against the reference, so a change in either the formula or the
        # reference has to be argued for deliberately.
        assert (low, high) == pytest.approx((0.31267, 0.831822), abs=1e-5)
        # A normal approximation would put this near 0.31-0.89; Wilson is wider
        # on the low side because it does not assume a large sample.
        assert low < 0.4
        assert high > 0.8

    def test_no_trials_is_none_not_an_error(self):
        assert wilson_interval(0, 0) is None

    @pytest.mark.parametrize("successes,trials", [(10, 10), (0, 10), (1, 10), (50, 100)])
    def test_degenerate_rates_stay_inside_the_unit_interval(self, successes, trials):
        """0% and 100% are where a normal approximation degenerates."""
        low, high = wilson_interval(successes, trials)
        assert 0.0 <= low <= 1.0
        assert 0.0 <= high <= 1.0
        assert low <= high

    def test_perfect_and_zero_successes_do_not_collapse(self):
        """A bare 0.0 or 1.0 would be wrong; Wilson keeps a real interval."""
        low, high = wilson_interval(10, 10)
        assert 0.0 < low < 1.0
        assert high <= 1.0

        low, high = wilson_interval(0, 10)
        assert low >= 0.0
        assert high < 1.0

    def test_interval_narrows_as_the_sample_grows(self):
        small = wilson_interval(6, 10)
        large = wilson_interval(600, 1000)
        assert (large[1] - large[0]) < (small[1] - small[0])

    def test_a_wider_z_widens_the_interval(self):
        narrow = wilson_interval(6, 10, z=1.0)
        wide = wilson_interval(6, 10, z=2.576)
        assert (wide[1] - wide[0]) > (narrow[1] - narrow[0])

    def test_matches_the_reference_across_a_grid(self):
        for trials in (5, 10, 20, 50):
            for successes in range(trials + 1):
                got = wilson_interval(successes, trials)
                ref = reference_wilson(successes, trials)
                assert got[0] == pytest.approx(ref[0], abs=1e-5), (successes, trials)
                assert got[1] == pytest.approx(ref[1], abs=1e-5), (successes, trials)


class TestExactMatchRate:
    def test_empty_is_none_rather_than_zero(self):
        """None means 'not measurable'. Zero would claim a total failure."""
        assert exact_match_rate([]) is None

    def test_all_and_none(self):
        assert exact_match_rate([("a", "a"), ("b", "b")]) == 1.0
        assert exact_match_rate([("a", "b"), ("c", "d")]) == 0.0

    def test_partial(self):
        assert exact_match_rate([("a", "a"), ("b", "c")]) == pytest.approx(0.5)

    def test_comparison_is_exact(self):
        """Case matters: this is exact match, not fuzzy matching."""
        assert exact_match_rate([("Trial", "trial")]) == 0.0


class TestNormalisedTitleSimilarity:
    def test_identical_titles(self):
        assert normalised_title_similarity("A study", "A study") == 1.0

    def test_case_and_punctuation_are_normalised_away(self):
        """Provider titles differ mainly by punctuation and case, not content."""
        assert normalised_title_similarity(
            "COVID-19: A Review.", "covid 19 a review"
        ) == 1.0

    def test_reordered_words_do_not_help(self):
        """This is Jaccard, not an edit distance: word order is not a match."""
        assert normalised_title_similarity("a b", "b a") == 1.0

    def test_partial_overlap(self):
        score = normalised_title_similarity("alpha beta gamma", "alpha beta delta")
        # intersection {alpha,beta} = 2, union {alpha,beta,gamma,delta} = 4
        assert score == pytest.approx(0.5)

    def test_both_empty_is_identical(self):
        assert normalised_title_similarity("", "") == 1.0
        assert normalised_title_similarity(None, None) == 1.0

    def test_one_empty_is_no_overlap(self):
        assert normalised_title_similarity("a study", "") == 0.0
        assert normalised_title_similarity(None, "a study") == 0.0

    def test_completely_different(self):
        assert normalised_title_similarity("alpha", "beta") == 0.0

    def test_is_symmetric(self):
        a, b = "some clinical trial", "clinical trial of some kind"
        assert normalised_title_similarity(a, b) == normalised_title_similarity(b, a)


class _Edge:
    """Stands in for CitationEdge, which graph_connectivity reads by attribute."""

    def __init__(self, source_paper_id: str, target_paper_id: str):
        self.source_paper_id = source_paper_id
        self.target_paper_id = target_paper_id


class TestGraphConnectivity:
    def test_no_papers(self):
        assert graph_connectivity([], []) == {
            "nodes": 0,
            "edges": 0,
            "dangling_edges": 0,
            "isolated_nodes": 0,
            "mean_degree": 0.0,
            "connected_fraction": 0.0,
        }

    def test_single_isolated_paper(self):
        out = graph_connectivity(["p1"], [])
        assert out["nodes"] == 1
        assert out["isolated_nodes"] == 1
        assert out["mean_degree"] == 0.0
        assert out["connected_fraction"] == 0.0

    def test_connected_chain(self):
        out = graph_connectivity(["a", "b", "c"], [_Edge("a", "b"), _Edge("b", "c")])
        assert out["nodes"] == 3
        assert out["edges"] == 2
        assert out["dangling_edges"] == 0
        assert out["isolated_nodes"] == 0
        # degree: a=1, b=2, c=1 -> mean 4/3
        assert out["mean_degree"] == pytest.approx(4 / 3)
        assert out["connected_fraction"] == pytest.approx(1.0)

    def test_dangling_edges_are_counted_not_connected(self):
        """An edge naming a paper outside the set must not create a node."""
        out = graph_connectivity(["a", "b"], [_Edge("a", "zzz")])
        assert out["edges"] == 1
        assert out["dangling_edges"] == 1
        assert out["nodes"] == 2
        assert out["isolated_nodes"] == 2
        assert out["connected_fraction"] == 0.0

    def test_partial_connectivity(self):
        out = graph_connectivity(
            ["a", "b", "c"], [_Edge("a", "b")]
        )
        assert out["isolated_nodes"] == 1
        assert out["connected_fraction"] == pytest.approx(2 / 3)

    def test_duplicate_paper_ids_collapse_to_one_node(self):
        out = graph_connectivity(["a", "a", "b"], [_Edge("a", "b")])
        assert out["nodes"] == 2

    def test_self_loop_counts_twice_in_degree(self):
        """Degree is incremented for both endpoints, so a self-loop adds 2."""
        out = graph_connectivity(["a"], [_Edge("a", "a")])
        assert out["dangling_edges"] == 0
        assert out["mean_degree"] == pytest.approx(2.0)


class TestClassificationScores:
    """The confusion-matrix scores the evaluation reports."""

    def test_perfect_prediction(self):
        s = ClassificationScores(true_positive=5, true_negative=5)
        assert s.support == 10
        assert s.precision == 1.0
        assert s.recall == 1.0
        assert s.specificity == 1.0
        assert s.f1 == 1.0
        assert s.accuracy == 1.0

    def test_empty_gives_none_everywhere_not_zero(self):
        """Zero would report a total failure for a metric that was never measured."""
        s = ClassificationScores()
        assert s.support == 0
        assert s.precision is None
        assert s.recall is None
        assert s.specificity is None
        assert s.f1 is None
        assert s.accuracy is None

    def test_known_values(self):
        s = ClassificationScores(
            true_positive=3, false_positive=1, true_negative=4, false_negative=2
        )
        assert s.support == 10
        assert s.precision == pytest.approx(0.75)
        assert s.recall == pytest.approx(0.6)
        assert s.specificity == pytest.approx(0.8)
        assert s.f1 == pytest.approx(2 * 0.75 * 0.6 / 1.35)
        assert s.accuracy == pytest.approx(0.7)

    def test_f1_is_none_when_precision_and_recall_cancel(self):
        """0 + 0 must not be a division by zero."""
        s = ClassificationScores(false_positive=3, false_negative=3)
        assert s.precision == 0.0
        assert s.recall == 0.0
        assert s.f1 is None

    def test_as_dict_carries_the_derived_fields(self):
        d = ClassificationScores(true_positive=1, true_negative=1).as_dict()
        for key in ("support", "precision", "recall", "specificity", "f1", "accuracy"):
            assert key in d
        assert d["true_positive"] == 1
