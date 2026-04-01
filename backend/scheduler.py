import schedule
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def get_news_file_path():
    """Get absolute path to news file (works locally and on Render)."""
    backend_dir = Path(__file__).parent
    project_root = backend_dir.parent
    news_file = project_root / "data" / "news" / "latest_news.json"
    return news_file

def scheduled_fetch():
    """Fetch news daily and append to existing articles."""
    logger.info("Starting scheduled news fetch...")
    try:
        # Lazy import keeps API startup resilient on hosts where optional
        # ingestion dependencies are temporarily unavailable.
        from backend.ingest_news_enhanced import fetch_news
        
        articles = fetch_news(days_back=1, max_per_feed=5)
        logger.info(f"✓ Scheduled fetch completed: {len(articles)} new articles fetched")
        
        # Log a sample of fetched articles
        if articles:
            for i, article in enumerate(articles[:2]):
                logger.info(f"  [{i+1}] {article.get('title', 'Untitled')[:60]}")
        
    except Exception as e:
        logger.error(f"✗ Scheduled fetch failed: {type(e).__name__}: {str(e)}")

def start_scheduler():
    """Start the background scheduler."""
    schedule.every().day.at("08:00").do(scheduled_fetch)
    
    logger.info("Scheduler started - will fetch news daily at 08:00")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    start_scheduler()