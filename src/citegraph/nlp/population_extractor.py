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
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            logger.warning("spaCy model not found. Using basic sentence splitting.")
            self.nlp = None

    def extract_candidates(self, paper_id: str, text: str, section: str = "unknown") -> List[PopulationCandidate]:
        """Extract population size candidates from text."""
        if not text:
            return []

        candidates = []
        
        # Split into sentences
        if self.nlp:
            doc = self.nlp(text)
            sentences = [sent.text for sent in doc.sents]
        else:
            # Fallback
            sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            # Check for ignore patterns first
            should_ignore = False
            for ignore_p in IGNORE_PATTERNS:
                if re.search(ignore_p, sentence):
                    # We don't necessarily ignore the whole sentence, 
                    # but it's a hint. For now, let's just proceed carefully.
                    pass

            for pattern_info in POPULATION_PATTERNS:
                matches = re.finditer(pattern_info["pattern"], sentence, re.IGNORECASE)
                for match in matches:
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
