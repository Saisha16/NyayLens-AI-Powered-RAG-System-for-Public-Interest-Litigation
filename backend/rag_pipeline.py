"""RAG Pipeline with Constitutional Database and Uploaded Legal Documents

Implements Retrieval-Augmented Generation using Indian Constitutional provisions,
uploaded legal PDFs (RTI Act, EP Act, BNSS), with relevance filtering and validation.
"""

from backend.constitutional_db import (
    retrieve_constitutional_provisions,
    get_legal_grounds,
    FUNDAMENTAL_RIGHTS,
    DIRECTIVE_PRINCIPLES,
    ADDITIONAL_PROVISIONS
)

# Module-level cache to avoid reloading legal_chunks.json on every request
_legal_chunks_cache = None
_bns_chunks_cache = None

def _get_cached_legal_chunks():
    """Load legal_chunks.json once and cache it."""
    global _legal_chunks_cache
    if _legal_chunks_cache is not None:
        return _legal_chunks_cache
    
    import json
    from pathlib import Path
    
    chunks_path = Path("data/legal_chunks.json")
    if not chunks_path.exists():
        _legal_chunks_cache = []
        return []
    
    try:
        with open(chunks_path, "r", encoding="utf-8") as f:
            _legal_chunks_cache = json.load(f)
        return _legal_chunks_cache
    except Exception:
        _legal_chunks_cache = []
        return []


def retrieve_legal_sections(issue_summary: str, topics: list = None, entities: list = None):
    """
    Retrieve ONLY relevant legal provisions that match the specific facts.
    Intelligent filtering ensures only applicable laws are included in PIL.
    
    APPROACH:
    - Select only the most relevant constitutional provisions for the specific issue
    - Retrieve only criminal law (BNS) sections that match the facts
    - Include supporting case laws that directly relate to the crime type
    
    Args:
        issue_summary: Brief summary of the issue from news article
        topics: List of classified topics (e.g., ['crime'])
        entities: List of named entities extracted from article
        
    Returns:
        List of dictionaries containing relevant legal references
    """
    if not topics:
        topics = ["general"]
    
    # Retrieve constitutional provisions - LIMIT to most relevant ones
    provisions = retrieve_constitutional_provisions(topics, issue_summary)
    
    legal_sections = []
    
    # Add ONLY the most critical Fundamental Right for this issue
    # Filter based on issue facts
    issue_lower = issue_summary.lower()
    selected_fr = None
    
    # Intelligent FR selection based on issue facts
    if any(word in issue_lower for word in ["killed", "murdered", "death", "violence", "assault", "rape", "sexual"]):
        selected_fr = FUNDAMENTAL_RIGHTS.get("life_liberty")  # Article 21 is most relevant
    elif any(word in issue_lower for word in ["child", "minor", "girl", "boy"]):
        selected_fr = FUNDAMENTAL_RIGHTS.get("exploitation") or FUNDAMENTAL_RIGHTS.get("child_labour")
    elif any(word in issue_lower for word in ["corruption", "bribe", "fraud"]):
        selected_fr = FUNDAMENTAL_RIGHTS.get("equality")  # Article 14
    else:
        selected_fr = provisions["fundamental_rights"][0] if provisions["fundamental_rights"] else None
    
    if selected_fr:
        legal_sections.append({
            "source": f"Constitution of India - {selected_fr['article']}",
            "title": selected_fr["title"],
            "excerpt": selected_fr["text"],
            "category": "Fundamental Right"
        })
    
    # Add the MOST RELEVANT Directive Principle (usually just 1-2)
    if provisions["directive_principles"]:
        # Take only the first 1-2 most applicable DPs
        for dp in provisions["directive_principles"][:2]:
            legal_sections.append({
                "source": f"Constitution of India - {dp['article']}",
                "title": dp["title"],
                "excerpt": dp["text"],
                "category": "Directive Principle"
            })
    
    # Add Article 32 (PIL jurisdiction)
    legal_sections.append({
        "source": f"Constitution of India - {ADDITIONAL_PROVISIONS['article_32']['article']}",
        "title": ADDITIONAL_PROVISIONS['article_32']["title"],
        "excerpt": ADDITIONAL_PROVISIONS['article_32']["text"],
        "category": "Constitutional Provision"
    })
    
    # Add ONLY relevant case laws (max 2-3)
    if provisions["case_laws"]:
        for case in provisions["case_laws"][:2]:  # Limit to top 2 most relevant cases
            legal_sections.append({
                "source": "Landmark Case Law",
                "title": case.split(" - ")[0] if " - " in case else case,
                "excerpt": case,
                "category": "Case Precedent"
            })

    # Identify if this is a crime issue
    crime_related_keywords = ["crime", "criminal", "offence", "offense", "law enforcement", 
                               "police", "arrest", "custody", "brutality", "corruption", 
                               "theft", "murder", "violence", "assault", "trafficking",
                               "killed", "death", "homicide", "lured", "deceit", "cheating",
                               "rape", "sexual", "kidnapping", "abduction"]
    is_crime_issue = any(keyword in issue_summary.lower() for keyword in crime_related_keywords) or \
                     any(topic in ["crime", "corruption", "law_enforcement"] for topic in topics)
    
    # Add BNS criminal law provisions ONLY if it's a crime issue
    if is_crime_issue:
        bns_sections = _get_bns_sections(issue_summary)
        if bns_sections:
            legal_sections.extend(bns_sections)
    
    # Add uploaded legal documents only if relevant
    try:
        from backend.semantic_similarity_enhanced import semantic_search
        
        # Use moderate threshold for uploaded legal docs
        min_threshold = 0.30
        top_k = 5 if is_crime_issue else 3
        
        semantic_matches = semantic_search(issue_summary, top_k=top_k, min_score=min_threshold)
        
        uploaded_doc_count = 0
        for m in semantic_matches:
            if not m.get("valid", True):
                continue
            
            # Skip if we already have this type of document
            if m.get("category") == "Uploaded Legal Document":
                if uploaded_doc_count >= 2:  # Limit to 2 uploaded docs
                    continue
                uploaded_doc_count += 1
            
            source = m["source"]
            excerpt = m["excerpt"]
            
            # Improve formatting for PDFs
            if m.get("category") == "Uploaded Legal Document":
                excerpt = _improve_text_formatting(excerpt)
            
            legal_sections.append({
                "source": source,
                "title": m["title"],
                "excerpt": excerpt[:800],  # Limit excerpt
                "category": m["category"],
                "similarity": m.get("similarity", 0.0),
                "relevance_reason": m.get("relevance_reason", "Related legal provision"),
            })
    
    except Exception as e:
        pass
    
    return legal_sections

def _improve_text_formatting(text: str) -> str:
    """
    Fix broken words first, then add proper spacing.
    Handles corrupted PDFs like "S ANHITA" and "Decem be r"
    """
    import re
    
    # Step 1: Fix broken words from corrupted PDFs
    text = re.sub(r'\b([A-Z])\s+([A-Z]{2,})\b', r'\1\2', text)  # "S ANHITA" -> "SANHITA"
    text = re.sub(r'\b([a-z]{1,3})\s+([a-z]{2,})\b', r'\1\2', text)  # "be r" -> "ber"
    text = text.replace(' IN ARY', 'INARY').replace('f or med', 'formed')
    text = text.replace('in tended', 'intended').replace('the reto', 'thereto')
    
    # Step 2: Add proper spacing where missing
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'([.!?;:,])([A-Za-z])', r'\1 \2', text)
    text = re.sub(r'([\)\]])([A-Za-z0-9])', r'\1 \2', text)
    text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)
    
    # Step 3: Cleanup multiple spaces
    text = re.sub(r' +', ' ', text)
    
    return text.strip()


def _get_bns_sections(issue_summary: str = "") -> list:
    """
    Fetch ONLY relevant BNS (Bhartiya Nyaya Sanhita) sections that match the specific facts.
    Uses precise matching to avoid including irrelevant provisions.
    """
    try:
        import json
        from pathlib import Path
        import re
        
        # Use cached legal chunks instead of reloading file
        chunks = _get_cached_legal_chunks()
        if not chunks:
            return []
        
        # Filter for BNS chunks
        bns_chunks = [c for c in chunks if "Bhartiya_Nyaya" in c.get("file", "") or "Bhartiya Nyaya Sanhita" in c.get("source", "")]
        
        issue_lower = issue_summary.lower()
        relevant_sections = []
        seen_ids = set()
        
        # Precise matching: crime type -> specific BNS sections
        # Each pattern returns a LIMITED set of most applicable sections (typically 2-4)
        crime_section_map = [
            # Pattern 1: Sexual intercourse by deceit/promise of marriage (Section 69)
            {
                'key': '69',
                'pattern': r'(promise.*marry|marriage.*promise|lured.*marriage|deceit.*sexual|false.*marriage|sexual.*deceit)',
                'sections': ['69'],
                'keywords': ['promise to marry', 'deceitful means', 'sexual intercourse', 'employing deceitful', 'deceitful'],
                'max_results': 1,
                'priority': 100
            },
            # Pattern 2: Murder
            {
                'key': '100-103',
                'pattern': r'(murder|killed|murdered|homicide|fatal|attacked)',
                'sections': ['100', '101', '102', '103'],
                'keywords': ['murder', 'punishment for murder', 'culpable homicide', 'causing death', 'fatal'],
                'max_results': 3,
                'priority': 95
            },
            # Pattern 3: Rape
            {
                'key': '64-66',
                'pattern': r'(rape|sexual.*assault|forced.*sex|non-consensual|without consent|forced himself|ignoring refusal)',
                'sections': ['64', '65', '66'],
                'keywords': ['rape', 'sexual assault', 'penetration', 'without consent', 'offence of rape', 'forced', 'refusal'],
                'max_results': 2,
                'priority': 90
            },
            # Pattern 4: Kidnapping/Abduction
            {
                'key': '137-139',
                'pattern': r'(kidnap|abduct|taken.*without|without.*consent.*taken|unlawful confinement|wrongfully|forcibly|taken.*on)',
                'sections': ['137', '138', '139'],
                'keywords': ['kidnapping', 'abduction', 'wrongfully concealing', 'unlawful confinement', 'child for purposes', 'taken', 'without consent'],
                'max_results': 1,
                'priority': 85
            },
            # Pattern 5: Dowry/Cruelty against women
            {
                'key': '85-86',
                'pattern': r'(dowry|cruelty.*wife|harassment.*marriage|bride.*burning|in-laws|sustained harassment)',
                'sections': ['85', '86'],  # Updated for actual BNS sections
                'keywords': ['dowry', 'cruelty', 'husband', 'bride', 'wife', 'harassment', 'in-laws', 'sustained'],
                'max_results': 1,
                'priority': 80
            },
            # Pattern 6: Assault/Hurt
            {
                'key': '351-355',
                'pattern': r'(assault|violence|hurt|injury|beating|attacked|struck.*with|struck.*rod|struck.*bottle)',
                'sections': ['353', '351', '352', '354', '355'],
                'keywords': ['assault', 'hurt', 'grievous hurt', 'causing injury', 'violence', 'intentional', 'struck', 'attacked'],
                'max_results': 1,
                'priority': 70
            },
            # Pattern 7: Theft/Robbery/Dacoity
            {
                'key': '303-310',
                'pattern': r'(theft|robbery|dacoity|burglary|stolen|extortion|snatch|snatched|pickpocket|chain)',
                'sections': ['303', '309', '310', '305', '306', '307', '308'],
                'keywords': ['theft', 'robbery', 'dacoity', 'extortion', 'stolen', 'snatch', 'snatched', 'burglary', 'pickpocket'],
                'max_results': 2,
                'priority': 65
            },
            # Pattern 8: Fraud/Cheating
            {
                'key': '318-320',
                'pattern': r'(fraud|cheating|forgery|impersonation|dishonestly|forged.*document|impersonate)',
                'sections': ['318', '319', '320'],
                'keywords': ['cheating', 'fraud', 'forgery', 'false document', 'dishonestly', 'impersonation'],
                'max_results': 2,
                'priority': 60
            },
        ]
        
        # Load extra matcher terms if available and extend keywords per pattern
        try:
            import json as _json
            terms_path = Path("data/matcher_terms.json")
            if terms_path.exists():
                extra = _json.load(open(terms_path, "r", encoding="utf-8"))
                for cp in crime_section_map:
                    key = cp.get('key')
                    if key and key in extra:
                        add = extra[key].get('extra_keywords', [])
                        existing = set(cp['keywords'])
                        cp['keywords'].extend([w for w in add if w not in existing])
        except Exception:
            pass
        
        # Load extra matcher terms if available and extend keywords per pattern
        try:
            import json as _json
            terms_path = Path("data/matcher_terms.json")
            if terms_path.exists():
                extra = _json.load(open(terms_path, "r", encoding="utf-8"))
                for cp in crime_section_map:
                    key = cp.get('key')
                    if key and key in extra:
                        add = extra[key].get('extra_keywords', [])
                        existing = set(cp['keywords'])
                        cp['keywords'].extend([w for w in add if w not in existing])
        except Exception:
            pass
        
        # Helper to extract a section number from chunk text
        def _extract_section_number(text: str) -> str:
            patterns = [
                r'Section\s+(\d+)',   # "Section 69"
                r'^(\d+)\.',          # "69." at start
                r'[\s\.]\s*(\d+)\.',  # " 69." in middle
                r'\b(\d+)\.\s+[A-Z]', # "69. Kidnapping" pattern
                r'Of\s+.*?\s+(\d+)\.' # "Of kidnapping... 137." pattern
            ]
            for p in patterns:
                m = re.search(p, text)
                if m:
                    return m.group(1)
            return ""

        # Find all matching patterns, then use only the highest priority match to avoid cross-family bleed
        matching_patterns = [cp for cp in crime_section_map if re.search(cp['pattern'], issue_lower)]
        matching_patterns.sort(key=lambda cp: cp.get('priority', 0), reverse=True)

        for crime_pattern in matching_patterns[:1]:  # only highest-priority match
            matched_count = 0
            max_to_include = crime_pattern.get('max_results', 2)
            # Prefer chunks that explicitly correspond to the targeted section numbers
            targeted_sections = set(crime_pattern.get('sections', []) or [])
            order_map = {sec: idx for idx, sec in enumerate(crime_pattern.get('sections', []) or [])}

            # Build candidate list: first, chunks whose extracted section number is in targeted_sections
            prioritized_chunks = []
            if targeted_sections:
                for chunk in bns_chunks:
                    if matched_count >= max_to_include:
                        break
                    chunk_id = chunk.get('id', '')
                    if chunk_id and chunk_id in seen_ids:
                        continue
                    sec_num = chunk.get('section_id') or _extract_section_number(chunk.get('text', ''))
                    if sec_num and sec_num in targeted_sections:
                        prioritized_chunks.append(chunk)
                # sort prioritized chunks so canonical sections come first
                prioritized_chunks.sort(key=lambda c: order_map.get(c.get('section_id') or _extract_section_number(c.get('text','')),'zzz'))

            # Fallback pool includes all BNS chunks if targeted ones are insufficient
            candidate_pool = prioritized_chunks if prioritized_chunks else bns_chunks

            for chunk in candidate_pool:
                if matched_count >= max_to_include:
                    break
                chunk_id = chunk.get('id', '')
                if chunk_id and chunk_id in seen_ids:
                    continue

                chunk_text = chunk.get('text', '')
                chunk_text_lower = chunk_text.lower()

                # Check if this chunk contains relevant keywords
                keyword_matches = sum(1 for kw in crime_pattern['keywords']
                                      if re.search(kw.replace('.', r'\.'), chunk_text_lower))

                # Require stronger keyword evidence for lower-priority families (cheating/dowry/theft)
                tougher_keys = {'85-86', '303-310', '318-320'}
                required_kw = 1  # keep permissive to retain recall

                # If pattern matched and chunk is from targeted sections, include it (no keyword check needed)
                sec_num = chunk.get('section_id') or (_extract_section_number(chunk_text) if targeted_sections else "")
                is_targeted = sec_num and sec_num in targeted_sections
                
                if is_targeted or keyword_matches >= required_kw:  # Adaptive keyword threshold
                    relevant_sections.append({
                        'chunk': chunk,
                        'priority': crime_pattern['priority'],
                        'keyword_match_count': keyword_matches if keyword_matches > 0 else 999,  # Boost targeted sections
                        'section_num': sec_num or ""
                    })
                    if chunk_id:
                        seen_ids.add(chunk_id)
                    matched_count += 1
        
        # Sort by priority, then by preferred section order within the matched crime family
        order_map = {sec: idx for idx, sec in enumerate((matching_patterns[:1][0].get('sections') or []))} if matching_patterns else {}
        relevant_sections.sort(key=lambda x: (
            -x['priority'],
            order_map.get(x.get('section_num'), 9999),
            -x['keyword_match_count']
        ))
        
        # Convert to legal_sections format
        bns_sections = []
        for item in relevant_sections:
            chunk = item['chunk']
            formatted_text = _improve_text_formatting(chunk.get("text", ""))
            
            section_num = chunk.get('section_id') or _extract_section_number(chunk.get('text', '')) or "Unknown"
            
            bns_sections.append({
                "source": chunk.get("source", "Bhartiya Nyaya Sanhita 2023"),
                "title": f"BNS Section {section_num}",
                "excerpt": formatted_text[:1000],  # Limit excerpt length
                "category": "Uploaded Legal Document",
                "similarity": 0.90,
                "relevance_reason": f"Directly applicable legal provision for {issue_summary[:50]}...",
            })
        # Semantic fallback: if rule-based retrieval found nothing, search embeddings restricted to BNS docs
        if not bns_sections:
            try:
                from backend.semantic_similarity_enhanced import semantic_search

                def _extract_any_section(text: str) -> str:
                    for pat in [
                        r"Section\s+(\d+)",
                        r"BNS Section\s+(\d+)",
                        r"\b(\d{1,4})\.\s",
                        r"\bSection\s+(\d{1,4})\b",
                    ]:
                        m = re.search(pat, text)
                        if m:
                            return m.group(1)
                    return ""

                fallback = semantic_search(issue_summary, top_k=5, min_score=0.35)
                for item in fallback:
                    # Only keep BNS documents
                    if "nyaya" not in item.get("source", "").lower():
                        continue
                    sec_num = _extract_any_section(item.get("title", "") + " " + item.get("excerpt", ""))
                    if not sec_num:
                        continue
                    if sec_num in seen_ids:
                        continue
                    bns_sections.append({
                        "source": item.get("source", "Bhartiya Nyaya Sanhita 2023"),
                        "title": f"BNS Section {sec_num}",
                        "excerpt": item.get("excerpt", "")[:1000],
                        "category": item.get("category", "Uploaded Legal Document"),
                        "similarity": item.get("similarity", 0.75),
                        "relevance_reason": item.get("relevance_reason", "Semantic fallback match"),
                    })
                    seen_ids.add(sec_num)
                    if len(bns_sections) >= 3:
                        break
            except Exception:
                pass
        return bns_sections
    except Exception as e:
        print(f"Error fetching BNS sections: {e}")
        return []


def get_jurisdiction_info(topics: list) -> dict:
    """
    Get appropriate jurisdiction and court information for PIL filing.
    
    Args:
        topics: List of classified topics
        
    Returns:
        Dictionary with jurisdiction details
    """
    return {
        "supreme_court": "Article 32 - Supreme Court jurisdiction for fundamental rights enforcement",
        "high_court": "Article 226 - High Court jurisdiction for fundamental rights and other matters",
        "recommended": "Supreme Court under Article 32" if any(t in ["human_trafficking", "corruption", "environment"] for t in topics) else "High Court under Article 226",
        "legal_grounds": get_legal_grounds(topics)
    }
