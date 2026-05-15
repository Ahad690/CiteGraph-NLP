import re

# Basic numeric patterns
NUMERIC_PATTERN = r'\d{1,3}(?:,\d{3})*(?:\.\d+)?'

# Patterns for population sizes
POPULATION_PATTERNS = [
    {
        "name": "N_EQUALS",
        "pattern": rf'\b[Nn]\s*=\s*({NUMERIC_PATTERN})\b',
        "type": "SAMPLE_SIZE_GENERIC",
        "weight": 0.8
    },
    {
        "name": "PATIENTS_COUNT",
        "pattern": rf'\b({NUMERIC_PATTERN})\s*(?:eligible\s+)?patients\b',
        "type": "TOTAL_ENROLLED",
        "weight": 0.7
    },
    {
        "name": "PARTICIPANTS_COUNT",
        "pattern": rf'\b({NUMERIC_PATTERN})\s*participants\b',
        "type": "TOTAL_ENROLLED",
        "weight": 0.7
    },
    {
        "name": "RANDOMIZED_COUNT",
        "pattern": rf'\b(?:randomized|assigned)\s+({NUMERIC_PATTERN})\b',
        "type": "TOTAL_RANDOMIZED",
        "weight": 0.9
    },
    {
        "name": "ENROLLED_COUNT",
        "pattern": rf'\benrolled\s+({NUMERIC_PATTERN})\b',
        "type": "TOTAL_ENROLLED",
        "weight": 0.85
    },
    {
        "name": "ANALYZED_COUNT",
        "pattern": rf'\banalyzed\s+({NUMERIC_PATTERN})\b',
        "type": "TOTAL_ANALYZED",
        "weight": 0.85
    },
    {
        "name": "COHORT_OF",
        "pattern": rf'\bcohort\s+of\s+({NUMERIC_PATTERN})\b',
        "type": "SAMPLE_SIZE_GENERIC",
        "weight": 0.75
    },
    {
        "name": "SAMPLE_SIZE_OF",
        "pattern": rf'\bsample\s+size\s+of\s+({NUMERIC_PATTERN})\b',
        "type": "SAMPLE_SIZE_GENERIC",
        "weight": 0.9
    }
]

# Patterns to ignore (false positives)
IGNORE_PATTERNS = [
    r'\b20\d{2}\b',  # Years
    r'\d+\s*%',      # Percentages
    r'[Pp]\s*<\s*0?\.\d+', # P-values
    r'95%\s*CI',     # Confidence intervals
    r'\d+\s*mg',     # Dosage
    r'p\s*=\s*\d+\.\d+' # P-values again
]
