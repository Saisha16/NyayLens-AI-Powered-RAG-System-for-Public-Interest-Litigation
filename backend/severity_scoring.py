"""Improved severity scoring for news articles with lemmatization.

Uses weighted keyword matching based on issue severity:
- Critical issues (murder, rape, trafficking): HIGH severity (0.7-1.0)
- Serious issues (corruption, pollution): MEDIUM severity (0.4-0.7)
- Other public interest: LOW-MEDIUM severity (0.2-0.4)

Now uses spaCy lemmatization to catch variants (murdered→murder, raped→rape).

Returns a float in [0, 1].
"""

from __future__ import annotations

import re
from typing import Iterable
try:
    import spacy
except ImportError:
    spacy = None

# Load spaCy model for lemmatization
if spacy:
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        nlp = None
else:
    nlp = None


# Critical severity keywords (directly indicate severe harm/violation)
CRITICAL_KEYWORDS = {
    "murder": 0.8,
    "homicide": 0.8,
    "killed": 0.8,
    "shot dead": 0.8,
    "shot": 0.75,
    "death": 0.75,
    "rape": 0.9,
    "sexual assault": 0.9,
    "trafficking": 0.85,
    "human trafficking": 0.9,
    "forced labour": 0.85,
    "bonded labor": 0.85,
    "child abuse": 0.85,
    "domestic violence": 0.8,
    "assault": 0.7,
    "violence": 0.65,
}

# High severity keywords (serious violations of rights/public interest)
HIGH_KEYWORDS = {
    "corruption": 0.65,
    "scam": 0.65,
    "fraud": 0.65,
    "embezzlement": 0.65,
    "bribery": 0.65,
    "pollution": 0.60,
    "contamination": 0.60,
    "hazard": 0.55,
    "disease": 0.55,
    "epidemic": 0.65,
    "pandemic": 0.70,
    "mistreatment": 0.60,
    "harassment": 0.55,
}

# Medium severity keywords (important public interest issues)
MEDIUM_KEYWORDS = {
    "education": 0.40,
    "school": 0.40,
    "health": 0.45,
    "hospital": 0.45,
    "sanitation": 0.40,
    "water": 0.45,
    "environment": 0.45,
    "forest": 0.45,
    "child": 0.50,
    "children": 0.50,
    "women": 0.40,
    "rights": 0.50,
    "human rights": 0.60,
}

# Modifiers that increase severity
SEVERITY_MULTIPLIERS = {
    "minor": 1.3,  # Crimes against minors are more serious
    "child": 1.3,
    "children": 1.3,
    "multiple": 1.2,  # Multiple victims/incidents
    "mass": 1.25,
    "widespread": 1.2,
}


def _lemmatize_text(text: str) -> str:
    """Convert text to lemmatized form to catch morphological variants."""
    if not nlp or not text:
        return text.lower()
    
    doc = nlp(text.lower())
    return " ".join([token.lemma_ for token in doc])


def calculate_severity(text: str, corpus_texts: Iterable[str] | None = None) -> float:
    """
    Compute severity score based on issue type and keywords with lemmatization.
    
    Parameters
    - text: the target article text
    - corpus_texts: iterable of other article texts (unused in new method)
    
    Returns: float in [0, 1]
    """
    if not text:
        return 0.0
    
    # Lemmatize text to catch variants (murdered→murder, raped→rape)
    text_lemmatized = _lemmatize_text(text)
    text_lower = text.lower()
    
    severity = 0.0
    max_found = 0.0
    
    # Check for critical keywords (these set a high floor)
    for keyword, weight in CRITICAL_KEYWORDS.items():
        keyword_lemmatized = _lemmatize_text(keyword)
        # Check both original and lemmatized forms
        if (re.search(r"\b" + re.escape(keyword) + r"\b", text_lower) or
            re.search(r"\b" + re.escape(keyword_lemmatized) + r"\b", text_lemmatized)):
            max_found = max(max_found, weight)
    
    # Check for high severity keywords
    if max_found == 0.0:
        for keyword, weight in HIGH_KEYWORDS.items():
            keyword_lemmatized = _lemmatize_text(keyword)
            if (re.search(r"\b" + re.escape(keyword) + r"\b", text_lower) or
                re.search(r"\b" + re.escape(keyword_lemmatized) + r"\b", text_lemmatized)):
                max_found = max(max_found, weight)
    
    # Check for medium severity keywords
    if max_found < 0.5:
        for keyword, weight in MEDIUM_KEYWORDS.items():
            keyword_lemmatized = _lemmatize_text(keyword)
            if (re.search(r"\b" + re.escape(keyword) + r"\b", text_lower) or
                re.search(r"\b" + re.escape(keyword_lemmatized) + r"\b", text_lemmatized)):
                max_found = max(max_found, weight)
    
    severity = max_found if max_found > 0 else 0.2  # Default to 0.2 for any news
    
    # Apply multipliers (increase severity if issue affects vulnerable groups)
    for modifier, multiplier in SEVERITY_MULTIPLIERS.items():
        if re.search(r"\b" + re.escape(modifier) + r"\b", text_lower):
            severity = min(1.0, severity * multiplier)
            break  # Only apply highest multiplier
    
    return max(0.0, min(1.0, severity))