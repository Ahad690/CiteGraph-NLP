import re

from citegraph.models.technical_evidence import TechnicalEvidence


COUNT_PATTERN = re.compile(
    r"\b(?P<number>\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*"
    r"(?P<scale>billion|million|thousand|[bmk])?\s+"
    r"(?P<unit>sentence pairs?|images?|examples?|samples?|documents?|instances?|records?|data points?)\b",
    re.IGNORECASE,
)
DATA_CONTEXT = re.compile(
    r"\b(dataset|data set|corpus|benchmark|train\w*|test\w*|validat\w*|evaluat\w*|collect\w*|used?|using)\b",
    re.IGNORECASE,
)
SCALE = {"billion": 1_000_000_000, "b": 1_000_000_000, "million": 1_000_000, "m": 1_000_000, "thousand": 1_000, "k": 1_000}
KIND_PRIORITY = {"training_examples": 3, "dataset_examples": 2, "evaluation_examples": 1}


class TechnicalEvidenceExtractor:
    def extract(self, paper_id: str, text: str | None, section: str = "abstract") -> TechnicalEvidence:
        if not text:
            return TechnicalEvidence(paper_id=paper_id, status="missing", explanation=f"No {section.replace('_', ' ')} available for technical dataset extraction.")

        candidates = []
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            if not DATA_CONTEXT.search(sentence):
                continue
            for match in COUNT_PATTERN.finditer(sentence):
                value = round(float(match.group("number").replace(",", "")) * SCALE.get((match.group("scale") or "").lower(), 1))
                if value <= 0 or value > 10_000_000_000:
                    continue
                context = sentence[max(0, match.start() - 100):match.start()]
                training = list(re.finditer(r"\btrain\w*\b", context, re.IGNORECASE))
                evaluation = list(re.finditer(r"\b(test\w*|evaluat\w*|benchmark)\b", context, re.IGNORECASE))
                if training or evaluation:
                    kind = "training_examples" if (training[-1].start() if training else -1) > (evaluation[-1].start() if evaluation else -1) else "evaluation_examples"
                else:
                    kind = "dataset_examples"
                confidence = (0.85 if kind == "training_examples" else 0.75) - (0.05 if section == "full_text" else 0)
                candidates.append((kind, value, match.group("unit").lower(), confidence, sentence.strip()))

        if not candidates:
            return TechnicalEvidence(paper_id=paper_id, status="missing", explanation=f"No explicit dataset-example count found in the {section.replace('_', ' ')}.")

        best = max(candidates, key=lambda item: (KIND_PRIORITY[item[0]], item[3], item[1]))
        competing = [item for item in candidates if item[0] == best[0] and abs(item[1] - best[1]) > best[1] * 0.1]
        ambiguous = bool(competing)
        return TechnicalEvidence(
            paper_id=paper_id,
            status="ambiguous" if ambiguous else "resolved",
            kind=best[0],
            value=best[1],
            unit=best[2],
            confidence=best[3] if not ambiguous else best[3] * 0.7,
            evidence=best[4],
            section=section,
            explanation=("Multiple different counts of the same kind appear; review the quoted sentence." if ambiguous
                         else f"Explicit dataset scale extracted from {section.replace('_', ' ')}. This is not a clinical population size."),
        )
