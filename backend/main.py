import logging
from fastapi import FastAPI, Query, Body, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import json
import time
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
import threading
from threading import Thread

# Optional rate limiting; start without if unavailable
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
except Exception:
    Limiter = None
    get_remote_address = None

# Use package-qualified imports so uvicorn loads correctly
from backend.nlp_pipeline import extract_issue
from backend.rag_pipeline import retrieve_legal_sections
from backend.pil_generator import generate_pil
from backend.latex_pdf_generator import LatexPDFGenerator
from backend.severity_scoring import calculate_severity
from backend.ingest_news_enhanced import add_custom_news
from backend.config import config
from backend.scheduler import start_scheduler
# Ensure logs directory exists before logger setup
os.makedirs("logs", exist_ok=True)
from backend.logger import logger
from backend.auth import authenticate_user, create_access_token
from backend.validators import (
    NewsArticleInput,
    PILGenerationInput,
    RefreshNewsInput,
    CustomPILRequest,
    sanitize_text,
)
from backend.explainability import SimpleExplainer
from backend.pil_manager import PILManager, PILDraft

# Helper function to get correct path to news file (works locally and on Render)
def get_news_file_path():
    """
    Resolves the correct path to latest_news.json relative to project root.
    Works both locally and on Render (where cwd might be backend/).
    Uses multiple strategies to find the FILE:
    1. Relative to this module (__file__)
    2. Relative to current working directory
    3. Check common Render deployment paths
    """
    # Strategy 1: Relative to this module (main.py in backend/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    path1 = os.path.join(project_root, "data", "news", "latest_news.json")
    if os.path.exists(path1):
        return path1
    
    # Strategy 2: Try from current working directory
    path2 = os.path.join(os.getcwd(), "data", "news", "latest_news.json")
    if os.path.exists(path2):
        return path2
    
    # Strategy 3: Try parent of cwd (in case cwd is backend/)
    path3 = os.path.join(os.getcwd(), "..", "data", "news", "latest_news.json")
    if os.path.exists(path3):
        return path3
    
    # Default to strategy 1 path (even if it doesn't exist yet)
    return path1

def ensure_news_file_exists():
    """Ensure news file exists. Create it from template if necessary."""
    news_file = get_news_file_path()
    
    if os.path.exists(news_file) and os.path.getsize(news_file) > 10:
        # File exists and has content
        return
    
    # Create parent directories if they don't exist
    os.makedirs(os.path.dirname(news_file), exist_ok=True)
    
    # Try to load from a backup location or embedded
    # For now, create an empty array to  allow the app to run
    # The scheduler will populate it on next daily run
    with open(news_file, 'w') as f:
        json.dump([], f)
    logger.info(f"Initialized empty news file at {news_file}")

app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    description=config.API_DESCRIPTION,
    contact={
        "name": "NyayLens Team",
        "url": "https://github.com/yourusername/pil26"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# Startup event: Ensure news file exists and spaCy model is available
@app.on_event("startup")
async def startup_events():
    """Initialize required files on app startup."""
    try:
        ensure_news_file_exists()
        logger.info("✅ News file initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize news file: {e}")
    
    logger.info("✅ Startup complete - Using NLP fallback mode (no spaCy on free tier)")
    logger.info("📝 App is ready to generate PILs using semantic analysis")

# Start scheduler in background thread
scheduler_thread = Thread(target=start_scheduler, daemon=True)
scheduler_thread.start()

# Rate limiting (optional)
if Limiter and get_remote_address:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
else:
    limiter = None

# Allow local frontend (file://, localhost) to call the API
# Handle wildcard CORS properly
cors_origins = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
    "http://localhost",
    "http://127.0.0.1",
    "file://",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=".*",
)

# Mount static files (frontend)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/", include_in_schema=False)
def root():
    """Serve the frontend application."""
    logger.info("Root endpoint accessed - serving frontend")
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    return FileResponse(frontend_path)

@app.get("/style.css", include_in_schema=False)
def serve_css():
    """Serve CSS file."""
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "frontend", "style.css"))

@app.get("/script.js", include_in_schema=False)
def serve_js():
    """Serve JavaScript file."""
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "frontend", "script.js"))

# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler with logging."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Please check logs."}
    )



@app.get("/api")
def api_info():
    """API information endpoint."""
    logger.info("API info endpoint accessed")
    return {
        "message": "NyayLens — AI-Powered PIL Generator",
        "version": config.API_VERSION
    }

@app.get("/health")
def health_check():
    """Detailed health check."""
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/debug/news-path")
def debug_news_path():
    """Debug endpoint to show resolved news file path and file status."""
    # Show all attempted paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    path1 = os.path.join(project_root, "data", "news", "latest_news.json")
    path2 = os.path.join(os.getcwd(), "data", "news", "latest_news.json")
    path3 = os.path.join(os.getcwd(), "..", "data", "news", "latest_news.json")
    
    news_file = get_news_file_path()
    exists = os.path.exists(news_file)
    size = os.path.getsize(news_file) if exists else 0
    count = 0
    if exists:
        try:
            with open(news_file) as f:
                data = json.load(f)
                count = len(data)
        except Exception as e:
            count = f"Error: {str(e)}"
    
    return {
        "resolved_path": news_file,
        "file_exists": exists,
        "file_size_bytes": size,
        "articles_count": count,
        "current_working_directory": os.getcwd(),
        "attempted_paths": {
            "strategy_1_from_module": {"path": path1, "exists": os.path.exists(path1)},
            "strategy_2_from_cwd": {"path": path2, "exists": os.path.exists(path2)},
            "strategy_3_from_cwd_parent": {"path": path3, "exists": os.path.exists(path3)}
        }
    }

@app.post("/token")
def login_for_access_token(username: str = Query(...), password: str = Query(...)):
    """
    Get JWT access token.
    
    Default credentials: username=demo, password=demo123
    """
    user = authenticate_user(username, password)
    if not user:
        logger.warning(f"Failed login attempt for user: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    access_token = create_access_token(user.username, user.user_id)
    logger.info(f"User logged in: {username}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.user_id,
        "username": user.username
    }



@app.get("/news")
def list_news(
    topic: str | None = Query(None), 
    date: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None)
):
    """Return available news items with optional filtering by topic and date.
    
    Query params:
    - topic: Filter by topic (e.g., environment, health)
    - date: Filter by date (YYYY for year, YYYY-MM for month, YYYY-MM-DD for specific date)
    - date_from: Start date for range filter (YYYY-MM-DD)
    - date_to: End date for range filter (YYYY-MM-DD)
    """
    news_file = get_news_file_path()
    if not os.path.exists(news_file):
        logger.warning("News file missing; returning empty list")
        return {"items": [], "total": 0}

    try:
        logger.info(f"News endpoint accessed with topic={topic}, date={date}, date_from={date_from}, date_to={date_to}")
        with open(news_file, "r", encoding="utf-8") as f:
            news = json.load(f)

        filtered = news
        
        # Filter by topic
        if topic:
            topic_lower = topic.lower()
            filtered = [n for n in filtered if topic_lower in [t.lower() for t in n.get("topics", [])]]
        
        # Filter by date (supports YYYY, YYYY-MM, or YYYY-MM-DD)
        if date:
            filtered = [n for n in filtered if (
                n.get("date", "").startswith(date) or 
                n.get("published", "").startswith(date)
            )]
        
        # Filter by date range
        if date_from or date_to:
            def get_date_str(item):
                return item.get("date") or (item.get("published", "").split()[0] if item.get("published") else "")
            
            if date_from and date_to:
                filtered = [n for n in filtered if date_from <= get_date_str(n) <= date_to]
            elif date_from:
                filtered = [n for n in filtered if date_from <= get_date_str(n)]
            elif date_to:
                filtered = [n for n in filtered if get_date_str(n) <= date_to]

        result = []
        for idx, item in enumerate(filtered):
            # Use normalized date field if available, fallback to published
            display_date = item.get("date") or (item.get("published", "").split()[0] if item.get("published") else "Unknown")
            
            result.append({
                "index": idx,
                "title": item.get("title", ""),
                "topics": item.get("topics", []),
                "summary": item.get("summary", item.get("text", "")[:240]),
                "excerpt": item.get("text", "")[:240] + ("..." if len(item.get("text", "")) > 240 else ""),
                "source": item.get("source", ""),
                "url": item.get("url", ""),
                "published": display_date,
                "text": item.get("text", "")[:600]  # Include fuller text for elaboration
            })
        
        logger.info(f"Returned {len(result)} news items")
        return {"items": result, "total": len(result)}
    except Exception as e:
        logger.error(f"Error loading news: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to load news")



@app.get("/topics")
def list_topics():
    news_file = get_news_file_path()
    if not os.path.exists(news_file):
        logger.warning("News file missing; returning empty topics")
        return {"topics": []}
    with open(news_file, "r", encoding="utf-8") as f:
        news = json.load(f)
    topics = set()
    for item in news:
        for t in item.get("topics", []):
            topics.add(t)
    return {"topics": sorted(topics)}


# Signal-based timeouts don't work on Render's threaded environment
# Just run functions directly; HTTP layer provides fallback timeout (~30s)


@app.get("/generate-pil")
def generate_pil_from_news(idx: int = Query(0, ge=0), topic: str | None = Query(None), full_rag: bool = Query(True)):
    """Generate PIL from news article using REAL RAG pipeline.
    
    Args:
        idx: Article index
        topic: Filter by topic
        full_rag: Use full NLP + RAG (True = real results)
    """
    start_time = time.time()
    logger.info(f"📄 REAL RAG PIPELINE RESTORED - Using NLP + Legal Retrieval")
    
    try:
        news_file = get_news_file_path()
        with open(news_file, "r", encoding="utf-8") as f:
            news = json.load(f)

        if topic:
            news = [n for n in news if topic.lower() in [t.lower() for t in n.get("topics", [])]]
        
        idx = min(idx or 0, len(news) - 1)
        article = news[idx]
        topics = article.get("topics", ["general"])
        article_text = f"{article.get('title', '')} {article.get('summary', '')}"
        
        # ✅ REAL NLP: Extract issue entities and summary
        logger.info("🔍 Extracting issue entities with spaCy...")
        issue = extract_issue(article_text)
        
        # ✅ REAL NLP: Calculate real severity score
        logger.info("📊 Calculating severity score...")
        severity_score = calculate_severity(article.get('summary', ''))
        priority_level = "HIGH" if severity_score > 0.7 else "MEDIUM" if severity_score > 0.4 else "LOW"
        
        # ✅ REAL RAG: Retrieve legal sections for this specific issue
        logger.info("⚖️ Retrieving relevant legal sections...")
        legal_sections = retrieve_legal_sections(
            issue_summary=issue.get('issue_summary', ''),
            topics=topics,
            entities=issue.get('entities', [])
        )
        
        # ✅ REAL GENERATION: Generate PIL with actual legal references
        logger.info("📝 Generating PIL with legal precedents...")
        pil_text = generate_pil(
            issue=issue,
            legal_sections=legal_sections,
            topics=topics,
            news_title=article['title'],
            severity_score=severity_score
        )
        
        # Create draft with real results
        draft = PILManager.create_draft(pil_text, idx, {
            "news_title": article['title'],
            "severity_score": severity_score,
            "priority_level": priority_level,
            "entities": issue.get('entities', []),
            "lite_mode": False
        })

        logger.info(f"✅ PIL generated in {round(time.time() - start_time, 2)}s - Severity: {severity_score:.2f}")
        
        return {
            "news_title": article['title'],
            "news_index": idx,
            "topics": topics,
            "summary": article.get('summary', '')[:200],
            "source": article.get('source', ''),
            "severity_score": round(severity_score, 2),
            "priority_level": priority_level,
            "entities": issue.get('entities', []),
            "draft_id": draft.id,
            "can_edit": True,
            "lite_mode": False,
            "generation_time_s": round(time.time() - start_time, 2),
            "pil_preview": pil_text[:500]  # Preview of full PIL
        }
    except Exception as e:
        logger.error(f"❌ Error in RAG pipeline: {str(e)}", exc_info=True)
        # Fallback to template if RAG fails
        try:
            logger.warning("⚠️ Falling back to template mode...")
            # Fallback template code here if needed
            raise HTTPException(status_code=500, detail=f"Detailed error: {str(e)}")
        except Exception as fallback_error:
            raise HTTPException(status_code=500, detail=str(fallback_error))


@app.post("/generate-pil")
def generate_pil_from_payload(payload: CustomPILRequest):
    """Generate a PIL from a custom article summary/text (POST-friendly).

    This unblocks clients that prefer POST bodies instead of query params and
    supports ad-hoc summaries beyond the stored news feed.
    """
    # Prefer richer article_text, fallback to summary
    raw_text = payload.article_text or payload.article_summary
    clean_text = sanitize_text(raw_text, max_length=12000)
    topics = payload.topics or ["general"]

    # NLP pass
    issue = extract_issue(clean_text)
    severity = calculate_severity(clean_text, [clean_text])

    legal_sections = retrieve_legal_sections(
        issue["issue_summary"],
        topics=topics,
        entities=payload.entities or issue["entities"]
    )

    pil_draft = generate_pil(
        issue,
        legal_sections,
        topics=topics,
        news_title=payload.title or "Custom Submission",
        severity_score=severity
    )

    priority_level = (
        "HIGH" if severity >= 0.75 else
        "MEDIUM" if severity >= 0.4 else
        "LOW"
    )

    metadata = {
        "news_title": payload.title or "Custom Submission",
        "severity_score": severity,
        "priority_level": priority_level,
        "entities_detected": payload.entities or issue["entities"],
        "legal_sources_used": [f"{l.get('category', 'Legal')}: {l['source']}" for l in legal_sections[:5]],
        "topics": topics,
        "source": payload.source or "custom"
    }

    draft = PILManager.create_draft(pil_draft, -1, metadata)

    return {
        "news_title": payload.title or "Custom Submission",
        "news_index": -1,
        "topics": topics,
        "summary": payload.article_summary,
        "source": payload.source or "custom",
        "published": datetime.utcnow().isoformat(),
        "excerpt": clean_text[:400],
        "severity_score": round(severity, 3),
        "priority_level": priority_level,
        "entities_detected": payload.entities or issue["entities"],
        "legal_sources_used": metadata["legal_sources_used"],
        "constitutional_grounds": len([l for l in legal_sections if l.get("category") in ["Fundamental Right", "Directive Principle"]]),
        "draft_id": draft.id,
        "can_edit": True
    }


@app.post("/add-custom-news")
def add_custom_news_endpoint(url: str = Query(...), title: str | None = Query(None)):
    """
    Add a custom news article from a URL.
    
    Args:
        url: URL of the article
        title: Optional custom title
    """
    result = add_custom_news(url, title)
    if result:
        return {"success": True, "article": result}
    else:
        return {"success": False, "error": "Failed to fetch and parse the URL"}


@app.post("/refresh-news")
def refresh_news(days_back: int = Query(7)):
    """
    Refresh news from RSS feeds for the last N days.
    
    Args:
        days_back: Fetch news from last N days (default: 7)
    """
    from backend.ingest_news_enhanced import fetch_news
    try:
        articles = fetch_news(days_back=days_back, max_per_feed=15)
        return {"success": True, "articles_fetched": len(articles), "message": f"Refreshed news from last {days_back} days"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/view-pil")
def view_pil_draft(draft_id: str = Query(None)):
    """
    View the current or specific PIL draft for editing
    Returns the full draft with all editable sections
    """
    if draft_id:
        draft = PILManager.get_draft(draft_id)
    else:
        draft = PILManager.get_current_draft()
    
    if not draft:
        return {"error": "No PIL draft available. Generate a PIL first."}

    # Ensure normalized and persisted (pull case precedents out of directives if embedded)
    PILManager.save_draft(draft)
    
    return draft.to_dict()


@app.post("/edit-pil")
def edit_pil_draft(draft_id: str = Query(...), updates: dict = Body(None)):
    """
    Edit specific sections of a PIL draft
    
    Can update:
    - facts_of_case
    - fundamental_rights (list)
    - directive_principles (list)
    - case_precedents (list)
    - prayer_relief
    """
    if not updates:
        return {"error": "No updates provided"}
    
    draft = PILManager.update_draft(draft_id, updates)
    
    if not draft:
        return {"error": f"Draft {draft_id} not found"}
    
    return {
        "success": True,
        "message": "PIL draft updated successfully",
        "draft": draft.to_dict()
    }


@app.get("/download-pil")
def download_pil(draft_id: str = Query(None)):
    """
    Download the generated PIL as PDF.
    Uses the edited draft if draft_id is provided, otherwise uses current draft.
    """
    if draft_id:
        draft = PILManager.get_draft(draft_id)
    else:
        draft = PILManager.get_current_draft()
    
    if not draft:
        return {"error": "No PIL draft available. Generate a PIL first."}

    # Normalize and persist so PDF gets updated case precedents
    PILManager.save_draft(draft)

    # Guarantee case precedents are present (fallback defaults if still empty)
    if not draft.case_precedents:
        draft.case_precedents = [
            "S.P. Gupta v. Union of India – Expanded locus standi in PIL",
            "Bandhua Mukti Morcha v. Union of India – Epistolary jurisdiction and access to justice",
            "People's Union for Democratic Rights v. Union of India – PIL for enforcement of fundamental rights",
            "D.K. Basu v. State of West Bengal – Custodial violence guidelines",
            "Nilabati Behera v. State of Orissa – Compensation for custodial death"
        ]
        PILManager.save_draft(draft)
    
    # Prepare PIL data dictionary for LaTeX PDF generation
    pil_data = {
        'date_of_filing': draft.created_at[:10] if draft.created_at else 'January 26, 2026',
        'issue': draft.news_title if draft.news_title else 'Public Interest Matter',
        'severity_score': f"{draft.severity_score:.2f} (High)" if draft.severity_score else '',
        'nature_of_issue': 'Violation of fundamental rights and public interest matter',
        'facts': draft.facts_of_case if isinstance(draft.facts_of_case, list) else [draft.facts_of_case] if draft.facts_of_case else [],
        'directive_principles': draft.directive_principles if draft.directive_principles else [],
        'relevant_case_precedents': draft.case_precedents if draft.case_precedents else []
    }
    
    # Generate PDF using LaTeX-based generator
    try:
        logger.info(f"Starting PDF generation for draft {draft.id}")
        logger.debug(f"PDF data: {pil_data}")
        pdf_generator = LatexPDFGenerator()
        pdf_bytes = pdf_generator.generate(pil_data)
        
        if not pdf_bytes:
            logger.error("PDF generation returned None")
            return {"error": "PDF generation failed", "details": "Generator returned empty"}
        
        logger.info(f"PDF generated successfully, size: {len(pdf_bytes)} bytes")
    except Exception as e:
        logger.error(f"PDF generation exception: {str(e)}", exc_info=True)
        return {"error": "PDF generation failed", "details": str(e)}
    
    # Return PDF as streaming response
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=PIL_{draft.id}.pdf"}
    )


# Explainability endpoints (future extension; require article db helper)
# @app.get("/explain-severity")
# async def explain_severity(article_id: int):
#     article = get_article(article_id)
#     return SimpleExplainer.explain_severity(article.text, article.severity_score).__dict__
#
# @app.get("/explain-pil/{article_id}")
# async def explain_pil(article_id: int):
#     article = get_article(article_id)
#     return SimpleExplainer.generate_pil_explanation_report({
#         'title': article.title,
#         'text': article.text,
#         'severity_score': article.severity_score,
#         'entities': article.entities,
#         'legal_sources_used': article.legal_sources
#     })


@app.get("/explain-pil")
def explain_pil_draft(draft_id: str = Query(None)):
    """
    Get explainability analysis for a PIL draft using SimpleExplainer.
    Shows reasoning behind severity score, entity detection, legal references, and viability.
    """
    if not draft_id:
        raise HTTPException(status_code=400, detail="draft_id required")
    
    try:
        draft = PILManager.get_draft(draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        # Reconstruct article data from draft
        article_data = {
            'title': draft.news_title,
            'text': draft.facts_of_case,
            'severity_score': draft.severity_score,
            'entities': draft.entities,
            'legal_sources_used': draft.legal_sources,
            'topics': draft.topics or []
        }
        
        # Generate explainability report
        report = SimpleExplainer.generate_pil_explanation_report(article_data)
        return report
        
    except Exception as e:
        logger.error(f"Error generating explainability: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate explanation")

