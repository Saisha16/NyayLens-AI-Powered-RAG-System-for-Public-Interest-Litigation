import os
from backend.config import config
import logging

# Conditional spacy import (won't break if not installed)
try:
    import spacy
except ImportError:
    spacy = None

logger = logging.getLogger("nyaylens")

# Lazy-load spacy model to avoid Render deployment timeouts
_nlp_model = None

def get_nlp_model():
    """Lazy-load spacy model on first use (or return None for fallback mode)"""
    global _nlp_model
    
    # Check if we're on Render (free tier) - skip spaCy to save memory
    if os.environ.get('RENDER') or os.environ.get('RENDER_USE_PAGER'):
        logger.info("🔍 Running on Render free tier - using NLP fallback mode")
        return None
    
    # Check if spacy is even installed
    if spacy is None:
        logger.info("🔍 spaCy not installed - using NLP fallback mode")
        return None
    
    if _nlp_model is None:
        try:
            logger.info("Loading spaCy model en_core_web_sm...")
            _nlp_model = spacy.load("en_core_web_sm")
            logger.info("✓ spaCy model loaded successfully")
        except (OSError, ImportError) as e:
            logger.warning(f"⚠️ spaCy model not found ({e}), using fallback")
            _nlp_model = False
            return None
    
    return _nlp_model if _nlp_model is not False else None

# Initialize model on first request, not on import
nlp = None


def extract_issue(article_text: str):
    """Extract entities and issue summary with optional LLM enhancement."""
    # Try LLM extraction if enabled
    if config.ENABLE_LLM_CLASSIFICATION:
        try:
            from backend.llm_integration import extract_legal_issues_llm
            llm_result = extract_legal_issues_llm(article_text)
            if llm_result:
                return llm_result
        except Exception:
            pass  # Fall back to spaCy
    
    # Fallback: spaCy-based extraction
    nlp_model = get_nlp_model()
    if nlp_model is None:
        # Fallback if spacy model unavailable
        logger.warning("spaCy model unavailable, using basic extraction")
        return {
            "issue_summary": article_text[:600],
            "entities": []
        }
    
    doc = nlp_model(article_text)

    entities = []
    for ent in doc.ents:
        if ent.label_ in ["GPE", "ORG", "PERSON", "LAW"]:
            entities.append(ent.text)

    issue_summary = article_text[:600]

    return {
        "issue_summary": issue_summary,
        "entities": list(set(entities))
    }
