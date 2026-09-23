import re
import uuid
import logging
from typing import List, Dict, Any, Optional
import spacy

from citegraph.models.population import PopulationCandidate
from citegraph.nlp.population_patterns import POPULATION_PATTERNS, IGNORE_PATTERNS

logger = logging.getLogger(__name__)

class PopulationExtractor:
    def __init__(self):
        # Only sentence boundaries are used here; the patterns do the rest. This
        # used to load en_core_web_sm and run its whole pipeline (tagger,
        # dependency parser, entity recogniser) on every paragraph just to read
        # doc.sents, which made extraction 62 of the 110 seconds of a 100-paper
        # run. The rule-based sentencizer is 30x faster on full text and 20x on
        # abstracts, and changed no gold-standard metric and no candidate across
        # 146 full-text paragraphs when the two were compared side by side.
        #
        # It also needs no model download, which matters more than it sounds:
        # the Docker image never installed en_core_web_sm, so production logged
        # "spaCy model not found" once at startup and ran a regex fallback,
        # while every evaluation ran the full model. Measured afterwards, all
        # three splitters give identical gold metrics, but that was luck; now
        # the evaluated code and the deployed code are the same code.
        self.nlp = spacy.blank("en")
        self.nlp.add_pipe("sentencizer")

    def extract_candidates(self, paper_id: str, text: str, section: str = "unknown") -> List[PopulationCandidate]:
        """Extract population size candidates from text."""
        if not text:
            return []

        candidates = []
        
        sentences = [sent.text for sent in self.nlp(text).sents]

        for sentence in sentences:
            # Locate the spans that must not be read as population sizes (years,
            # percentages, p-values, dosages). These are matched per-span rather
            # than per-sentence: skipping the whole sentence discarded every
            # genuine count that merely shared a sentence with a date, which is
            # most of them ("...1099 patients ... through January 29, 2020").
            ignore_spans = [
                match.span()
                for ignore_p in IGNORE_PATTERNS
                for match in re.finditer(ignore_p, sentence)
            ]

            for pattern_info in POPULATION_PATTERNS:
                matches = re.finditer(pattern_info["pattern"], sentence, re.IGNORECASE)
                for match in matches:
                    # Only reject when the captured number itself sits inside an
                    # ignored span, not when one appears elsewhere in the sentence.
                    number_start, number_end = match.span(1)
                    if any(start < number_end and number_start < end
                           for start, end in ignore_spans):
                        continue

                    raw_value = match.group(1).replace(',', '')
                    try:
                        value = int(float(raw_value))
                    except ValueError:
                        continue

                    # Basic sanity check
                    if value <= 0 or value > 10000000:
                        continue

                    # Confidence calculation
                    confidence = pattern_info["weight"]
                    
                    # Section bonus
                    section_bonus = 0.0
                    if section.lower() in ["abstract", "methods"]:
                        section_bonus = 0.1
                    
                    confidence = min(1.0, confidence + section_bonus)

                    candidate = PopulationCandidate(
                        candidate_id=str(uuid.uuid4()),
                        paper_id=paper_id,
                        value=value,
                        raw_text=match.group(0),
                        sentence=sentence.strip(),
                        section=section,
                        semantic_type=pattern_info["type"],
                        start_char=match.start(),
                        end_char=match.end(),
                        extraction_method="regex",
                        confidence=confidence
                    )
                    candidates.append(candidate)

        return candidates
