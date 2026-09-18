"""Metric computation for the evaluation plan in the project proposal (S13).

Kept deliberately small and dependency-free so every number in the thesis can
be recomputed by running one script.
"""

from dataclasses import dataclass, asdict
from typing import Any, Optional, Sequence


@dataclass
class ClassificationScores:
    """Counts and derived rates for a binary decision."""

    true_positive: int = 0
    false_positive: int = 0
    true_negative: int = 0
    false_negative: int = 0

    @property
    def support(self) -> int:
        return (self.true_positive + self.false_positive
                + self.true_negative + self.false_negative)

    @property
    def precision(self) -> Optional[float]:
        denominator = self.true_positive + self.false_positive
        return self.true_positive / denominator if denominator else None

    @property
    def recall(self) -> Optional[float]:
        denominator = self.true_positive + self.false_negative
        return self.true_positive / denominator if denominator else None

    @property
    def specificity(self) -> Optional[float]:
        denominator = self.true_negative + self.false_positive
        return self.true_negative / denominator if denominator else None

    @property
    def f1(self) -> Optional[float]:
        p, r = self.precision, self.recall
        if p is None or r is None or (p + r) == 0:
            return None
        return 2 * p * r / (p + r)

    @property
    def accuracy(self) -> Optional[float]:
        return (self.true_positive + self.true_negative) / self.support if self.support else None

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.update({
            "support": self.support,
            "precision": self.precision,
            "recall": self.recall,
            "specificity": self.specificity,
            "f1": self.f1,
            "accuracy": self.accuracy,
        })
        return d


def wilson_interval(successes: int, trials: int, z: float = 1.96) -> Optional[tuple]:
    """95% Wilson score interval.

    Reported instead of a bare proportion because the gold set is small; a
    normal approximation is unreliable at n=20 and degenerates at 0% or 100%.
    """
    if trials == 0:
        return None
    p = successes / trials
    denominator = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denominator
    margin = z * ((p * (1 - p) / trials + z * z / (4 * trials * trials)) ** 0.5) / denominator
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def exact_match_rate(pairs: Sequence[tuple]) -> Optional[float]:
    """Fraction of (predicted, expected) pairs that are exactly equal."""
    if not pairs:
        return None
    return sum(1 for predicted, expected in pairs if predicted == expected) / len(pairs)


def normalised_title_similarity(a: Optional[str], b: Optional[str]) -> float:
    """Token-level Jaccard similarity, lowercased and punctuation-stripped.

    Used rather than an edit distance because provider titles differ mainly by
    subtitle and punctuation, not by character-level noise.
    """
    import re

    def tokens(value: Optional[str]) -> set:
        if not value:
            return set()
        return set(re.sub(r"[^a-z0-9 ]", " ", value.lower()).split())

    ta, tb = tokens(a), tokens(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def graph_connectivity(paper_ids: Sequence[str], edges: Sequence[Any]) -> dict[str, Any]:
    """Structural health of a produced citation graph."""
    ids = set(paper_ids)
    degree: dict[str, int] = {pid: 0 for pid in ids}
    dangling = 0
    for edge in edges:
        source = getattr(edge, "source_paper_id", None)
        target = getattr(edge, "target_paper_id", None)
        if source not in ids or target not in ids:
            dangling += 1
            continue
        degree[source] += 1
        degree[target] += 1
    isolated = [pid for pid, d in degree.items() if d == 0]
    return {
        "nodes": len(ids),
        "edges": len(edges),
        "dangling_edges": dangling,
        "isolated_nodes": len(isolated),
        "mean_degree": (sum(degree.values()) / len(ids)) if ids else 0.0,
        "connected_fraction": ((len(ids) - len(isolated)) / len(ids)) if ids else 0.0,
    }
