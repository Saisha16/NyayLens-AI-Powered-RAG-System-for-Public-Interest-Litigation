"""Enhanced semantic search with uploaded legal documents and relevance filtering.

Integrates constitutional DB + uploaded PDFs (RTI Act, EP Act, BNSS, etc.)
with relevance scoring and validation.
"""

from __future__ import annotations

import numpy as np
import faiss
import json
import pickle
import warnings
from pathlib import Path
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer

# Suppress benign model loading warnings
warnings.filterwarnings("ignore", message=".*embeddings.position_ids.*")

from backend.constitutional_db import (
    FUNDAMENTAL_RIGHTS,
    DIRECTIVE_PRINCIPLES,
    ADDITIONAL_PROVISIONS,
    TOPIC_CONSTITUTIONAL_MAPPING,
)


# Module-level singletons
_model: SentenceTransformer | None = None
_index: faiss.IndexFlatIP | None = None
_corpus: List[Dict] | None = None
_embeddings: np.ndarray | None = None

# Relevance threshold
RELEVANCE_THRESHOLD = 0.30  # Only return matches with similarity >= 0.30


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-mpnet-base-v2")
    return _model


def _build_corpus() -> List[Dict]:
    """Collect constitutional articles, DPSPs, case laws, and uploaded legal docs."""
    items: List[Dict] = []

    # Fundamental Rights
    for key, fr in FUNDAMENTAL_RIGHTS.items():
        items.append({
            "id": f"fr_{key}",
            "title": fr.get("title", ""),
            "text": fr.get("text", ""),
            "source": fr.get("article", "Fundamental Right"),
            "category": "Fundamental Right",
        })

    # DPSPs
    for key, dp in DIRECTIVE_PRINCIPLES.items():
        items.append({
            "id": f"dp_{key}",
            "title": dp.get("title", ""),
            "text": dp.get("text", ""),
            "source": dp.get("article", "Directive Principle"),
            "category": "Directive Principle",
        })

    # Additional provisions
    for key, ap in ADDITIONAL_PROVISIONS.items():
        items.append({
            "id": f"ap_{key}",
            "title": ap.get("title", ""),
            "text": ap.get("text", ""),
            "source": ap.get("article", "Constitution"),
            "category": "Constitutional Provision",
        })

    # Case laws from topic mappings
    seen_cases = set()
    for topic, mapping in TOPIC_CONSTITUTIONAL_MAPPING.items():
        for case in mapping.get("key_case_laws", []):
            if case not in seen_cases:
                seen_cases.add(case)
                title = case.split(" - ")[0] if " - " in case else case
                items.append({
                    "id": f"case_{len(seen_cases)}",
                    "title": title,
                    "text": case,
                    "source": "Landmark Case Law",
                    "category": "Case Precedent",
                })

    # Load uploaded legal documents (RTI, EP Act, BNSS, etc.)
    legal_chunks_path = Path("data/legal_chunks.json")
    if legal_chunks_path.exists():
        try:
            with open(legal_chunks_path, "r", encoding="utf-8") as f:
                legal_chunks = json.load(f)
            
            for chunk in legal_chunks:
                section_id = chunk.get("section_id")
                chunk_title = chunk.get("title", "").strip()
                source = chunk.get("source", "Legal Document")

                if section_id:
                    title = f"{source} Section {section_id}: {chunk_title}" if chunk_title else f"{source} Section {section_id}"
                else:
                    title = f"{source} - Sec {chunk.get('chunk_index', 0)}"

                items.append({
                    "id": chunk.get("id", "unknown"),
                    "title": title,
                    "text": chunk.get("text", ""),
                    "source": source,
                    "category": "Uploaded Legal Document",
                    "file": chunk.get("file", ""),
                    "section_id": section_id,
                })
        except Exception as e:
            print(f"Warning: Could not load legal_chunks.json: {e}")

    return items


def _init_index():
    """Initialize corpus and FAISS index once (with caching)."""
    import os
    global _index, _corpus, _embeddings
    
    # Skip index build on Render free tier to prevent timeout
    if os.environ.get('RENDER') or os.environ.get('RENDER_USE_PAGER'):
        return
    
    if _index is not None:
        return

    cache_file = Path("data/semantic_cache.pkl")
    _corpus = _build_corpus()
    
    # Try to load from cache
    if cache_file.exists():
        try:
            print("Loading semantic index from cache...")
            with open(cache_file, "rb") as f:
                cache_data = pickle.load(f)
            
            # Verify corpus hasn't changed
            if len(cache_data["corpus"]) == len(_corpus):
                _embeddings = cache_data["embeddings"]
                dim = _embeddings.shape[1]
                _index = faiss.IndexFlatIP(dim)
                _index.add(_embeddings)
                print(f"✓ Loaded {len(_corpus)} documents from cache")
                return
        except Exception as e:
            print(f"Cache load failed: {e}, rebuilding...")
    
    # Build embeddings from scratch
    model = _get_model()
    texts = [item["text"] for item in _corpus]
    
    print(f"Building semantic index for {len(texts)} legal documents (first time, ~30s)...")
    _embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        batch_size=16,
        show_progress_bar=True
    ).astype("float32")

    dim = _embeddings.shape[1]
    _index = faiss.IndexFlatIP(dim)
    _index.add(_embeddings)
    
    # Save to cache
    try:
        with open(cache_file, "wb") as f:
            pickle.dump({"corpus": _corpus, "embeddings": _embeddings}, f)
        print(f"[OK] Semantic index ready and cached ({len(_corpus)} documents)")
    except Exception as e:
        print(f"[WARN] Cache save failed: {e}")
        print(f"[OK] Semantic index ready ({len(_corpus)} documents)")


def semantic_search(query: str, top_k: int = 10, min_score: float = RELEVANCE_THRESHOLD) -> List[Dict]:
    """Return top-k semantically similar legal references above relevance threshold.

    Args:
        query: Issue summary or legal question
        top_k: Maximum results to return
        min_score: Minimum similarity score (0-1); lower = more permissive

    Returns:
        List of relevant legal references with source, title, excerpt, category, similarity, and reason.
    """
    import os
    
    if not query or len(query.strip()) == 0:
        return []

    # Skip semantic search on Render free tier to avoid timeout (30s limit)
    if os.environ.get('RENDER') or os.environ.get('RENDER_USE_PAGER'):
        return []  # Return empty to skip expensive semantic search

    _init_index()
    model = _get_model()

    q = model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
    scores, idxs = _index.search(q, top_k * 2)  # Fetch extra for filtering
    idxs = idxs[0]
    scores = scores[0]

    results: List[Dict] = []
    for i, score in zip(idxs, scores):
        if score < min_score:
            continue  # Filter low-relevance results
        
        item = _corpus[i]
        
        # Build validation reason
        reason = _validate_relevance(query, item, float(score))
        
        results.append({
            "source": item["source"],
            "title": item["title"],
            "excerpt": item["text"][:400],
            "category": item["category"],
            "similarity": float(score),
            "relevance_reason": reason,
            "valid": score >= RELEVANCE_THRESHOLD,
        })
        
        if len(results) >= top_k:
            break

    return results


def _validate_relevance(query: str, item: Dict, score: float) -> str:
    """Generate explanation for why this legal reference is relevant (or not)."""
    if score >= 0.60:
        return f"Highly relevant to issue (similarity: {score:.2f})"
    elif score >= 0.40:
        return f"Moderately relevant; may support legal argument (similarity: {score:.2f})"
    elif score >= RELEVANCE_THRESHOLD:
        return f"Weakly relevant; provides contextual support (similarity: {score:.2f})"
    else:
        return f"Low relevance; excluded from PIL (similarity: {score:.2f})"


def search_uploaded_legal_docs(query: str, top_k: int = 5) -> List[Dict]:
    """Search only uploaded legal documents (RTI, EP Act, BNSS, etc.)."""
    all_results = semantic_search(query, top_k=50, min_score=0.25)
    
    # Filter to only uploaded docs
    uploaded_only = [
        r for r in all_results
        if r.get("category") == "Uploaded Legal Document"
    ]
    
    return uploaded_only[:top_k]
