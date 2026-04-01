import schedule
import time
import logging

logger = logging.getLogger(__name__)

def scheduled_fetch():
    """Fetch news daily and append to existing articles."""
    logger.info("Starting scheduled news fetch...")
    try:
        # Lazy import keeps API startup resilient on hosts where optional
        # ingestion dependencies are temporarily unavailable.
        from backend.ingest_news_enhanced import fetch_news
        articles = fetch_news(days_back=1, max_per_feed=5)
        logger.info(f"Fetched {len(articles)} new articles")
    except Exception as e:
        logger.error(f"Scheduled fetch failed: {e}")

def start_scheduler():
    """Start the background scheduler."""
    schedule.every().day.at("08:00").do(scheduled_fetch)
    
    logger.info("Scheduler started - will fetch news daily at 08:00")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    start_scheduler()