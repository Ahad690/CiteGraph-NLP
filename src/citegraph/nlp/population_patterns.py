import re

# Basic numeric patterns
NUMERIC_PATTERN = r'\d+(?:,\d{3})*(?:\.\d+)?'

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
        "name": "NUMBER_RANDOMIZED",
        "pattern": rf'\b({NUMERIC_PATTERN})\s+(?:patients|participants|individuals|subjects)\s+(?:were\s+)?(?:randomized|assigned|enrolled)\b',
        "type": "TOTAL_RANDOMIZED",
        "weight": 0.95
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
    },
    # --- phrasings the original set missed -------------------------------
    # Observational and epidemiological papers rarely say "patients were
    # randomized"; they report cases, subjects or a plain total.
    {
        "name": "TOTAL_OF",
        "pattern": rf'\ba\s+total\s+of\s+({NUMERIC_PATTERN})\b',
        "type": "SAMPLE_SIZE_GENERIC",
        "weight": 0.85
    },
    {
        "name": "CASES_COUNT",
        "pattern": rf'\b({NUMERIC_PATTERN})\s+(?:laboratory-|lab-|virologically\s+)?(?:confirmed\s+|reported\s+|suspected\s+|index\s+)?cases\b',
        "type": "SAMPLE_SIZE_GENERIC",
        "weight": 0.7
    },
    {
        "name": "SUBJECTS_COUNT",
        "pattern": rf'\b({NUMERIC_PATTERN})\s+(?:healthy\s+|consecutive\s+|adult\s+)?(?:subjects|individuals|volunteers|adults|children|infants|women|men)\b',
        "type": "TOTAL_ENROLLED",
        "weight": 0.7
    },
    {
        "name": "CONSECUTIVE_PATIENTS",
        "pattern": rf'\b({NUMERIC_PATTERN})\s+consecutive\s+(?:patients|cases|subjects)\b',
        "type": "TOTAL_ENROLLED",
        "weight": 0.8
    },
    {
        "name": "INCLUDED_COUNT",
        "pattern": rf'\b(?:included|recruited|studied|evaluated|assessed)\s+({NUMERIC_PATTERN})\b',
        "type": "TOTAL_ANALYZED",
        "weight": 0.8
    },
    {
        "name": "DATA_FROM",
        "pattern": rf'\bdata\s+(?:on|from|regarding)\s+(?:the\s+first\s+)?({NUMERIC_PATTERN})\b',
        "type": "TOTAL_ANALYZED",
        "weight": 0.75
    },
    # Semantic types the README documents but no pattern ever produced.
    # Kept as two single-group patterns: the extractor reads group(1), so an
    # alternation with a capture group in each branch would yield None.
    {
        "name": "SCREENED_COUNT",
        "pattern": rf'\bscreened\s+({NUMERIC_PATTERN})\b',
        "type": "SCREENED",
        "weight": 0.8
    },
    {
        "name": "WERE_SCREENED",
        "pattern": rf'\b({NUMERIC_PATTERN})\s+(?:patients\s+|participants\s+|subjects\s+)?(?:were\s+)?screened\b',
        "type": "SCREENED",
        "weight": 0.8
    },
    {
        "name": "COMPLETED_COUNT",
        "pattern": rf'\b({NUMERIC_PATTERN})\s+(?:patients\s+|participants\s+|subjects\s+)?completed\b',
        "type": "COMPLETERS",
        "weight": 0.75
    },
    {
        "name": "ARM_SIZE_GROUP",
        "pattern": rf'\b(?:group|arm)\s+\(\s*[Nn]\s*=\s*({NUMERIC_PATTERN})\s*\)',
        "type": "ARM_SIZE",
        "weight": 0.7
    },
    {
        "name": "FOLLOWED_UP",
        "pattern": rf'\b({NUMERIC_PATTERN})\s+(?:patients\s+|participants\s+)?(?:were\s+)?followed\s+(?:up|for)\b',
        "type": "FOLLOWUP_COUNT",
        "weight": 0.7
    },
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
