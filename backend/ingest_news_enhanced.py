"""Enhanced news ingestion with date filtering, summarization, and custom URLs."""

import feedparser
from newspaper import Article
import uuid
import json
from datetime import datetime, timedelta
try:
    import spacy
except ImportError:
    spacy = None
from collections import Counter
import os
from typing import Optional
import re
import html as html_unescape
import requests
import signal
from contextlib import contextmanager

# Timeout handler for article downloads
class TimeoutException(Exception):
    pass

@contextmanager
def timeout(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Article download timeout")
    # Set the signal handler and alarm
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

# Lazy-load spaCy with a lightweight pipeline; fall back to blank model on memory errors
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is not None:
        return _nlp

    # spaCy is optional on constrained hosts (e.g., Render free tier).
    if spacy is None:
        return None

    try:
        _nlp = spacy.load(
            "en_core_web_sm",
            disable=["lemmatizer", "tagger", "attribute_ruler", "parser"],
        )
        if "sentencizer" not in _nlp.pipe_names:
            _nlp.add_pipe("sentencizer")
    except MemoryError:
        _nlp = spacy.blank("en")
        _nlp.add_pipe("sentencizer")
    except Exception:
        _nlp = spacy.blank("en")
        _nlp.add_pipe("sentencizer")

    return _nlp

# Optimized RSS feeds (fast, reliable sources)
RSS_FEEDS = [
    # Major Indian National News
    "https://www.thehindu.com/news/national/feeder/default.rss",
    "https://indianexpress.com/section/india/feed/",
    "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    
    # Legal & Judicial News (critical for PIL)
    "https://www.livelaw.in/feed",  # Legal news and court updates
    "https://www.barandbench.com/feed",  # Legal journalism
    
    # Investigative & Social Issues
    "https://thewire.in/feed",  # In-depth investigative reporting
    "https://scroll.in/feeds/all",  # Long-form journalism
    
    # Additional Mainstream Sources
    "https://www.ndtv.com/india-news/rss",  # NDTV India news
    "https://www.news18.com/rss/india.xml",  # News18 India
    
    # Human Rights & Social Justice
    "https://www.deccanherald.com/rss/national.xml",  # Deccan Herald
    "https://www.business-standard.com/rss/home_page_top_stories.rss",  # Business Standard (policy news)
    
    # Additional Topic-Specific Feeds
    "https://www.thehindu.com/news/cities/feeder/default.rss",  # City news (local issues)
    "https://www.thehindu.com/sci-tech/energy-and-environment/feeder/default.rss",  # Environment
    "https://indianexpress.com/section/cities/feed/",  # Cities section
]

# Twitter/Nitter RSS feeds for rapid social updates (best-effort; may be blocked)
TWITTER_RSS = [
]

# Enhanced topic keywords
TOPIC_KEYWORDS = {
    "environment": {
        "primary": ["pollution", "climate change", "deforestation", "greenhouse", "carbon emission", "global warming"],
        "secondary": ["environment", "forest", "river", "air quality", "water", "waste", "renewable energy"]
    },
    "human_trafficking": {
        "primary": ["human trafficking", "sex trafficking", "forced labour", "bonded labor"],
        "secondary": ["trafficking", "smuggling", "exploitation", "slavery"]
    },
    "health": {
        "primary": ["epidemic", "pandemic", "outbreak", "disease", "virus", "vaccine"],
        "secondary": ["hospital", "health", "medical", "clinic", "patient", "doctor"]
    },
    "education": {
        "primary": ["education policy", "school reform", "university", "literacy"],
        "secondary": ["school", "college", "education", "students", "teacher", "learning"]
    },
    "corruption": {
        "primary": ["corruption scandal", "bribery", "embezzlement", "graft"],
        "secondary": ["scam", "corruption", "bribe", "fraud", "misappropriation"]
    },
    "crime": {
        "primary": ["murder", "homicide", "assault", "robbery", "criminal"],
        "secondary": ["arrest", "crime", "police", "theft", "investigation"]
    },
    "women_children": {
        "primary": ["child abuse", "domestic violence", "women's rights", "gender violence"],
        "secondary": ["women", "girls", "minor", "child", "rape", "harassment"]
    },
    "public_health": {
        "primary": ["sanitation crisis", "water contamination", "sewage", "public hygiene"],
        "secondary": ["sanitation", "drinking water", "waste management", "hygiene"]
    },
}


def classify_topics_nlp(text: str):
    """Classify article into topics using NLP and keyword matching."""
    nlp = _get_nlp()
    doc = nlp(text.lower()) if nlp is not None else None
    text_lower = text.lower()
    
    topic_scores = {}
    
    for topic, keyword_groups in TOPIC_KEYWORDS.items():
        score = 0
        
        for kw in keyword_groups["primary"]:
            if kw in text_lower:
                score += 2
        
        for kw in keyword_groups["secondary"]:
            if kw in text_lower:
                score += 1
        
        if score > 0:
            topic_scores[topic] = score
    
    entities = []
    if doc is not None:
        entities = [ent.text.lower() for ent in doc.ents if ent.label_ in ["ORG", "GPE", "LAW", "EVENT"]]
    
    entity_text = " ".join(entities)
    if "ministry" in entity_text or "government" in entity_text:
        if "corruption" in topic_scores:
            topic_scores["corruption"] += 1
    
    if "school" in entity_text or "university" in entity_text:
        if "education" in topic_scores:
            topic_scores["education"] += 1
    
    if "hospital" in entity_text or "WHO" in entity_text:
        if "health" in topic_scores:
            topic_scores["health"] += 1
    
    selected_topics = [topic for topic, score in topic_scores.items() if score >= 2]
    
    return selected_topics if selected_topics else ["general"]


def extract_summary(text: str, max_sentences: int = 3) -> str:
    """
    Extract a concise summary from article text using NLP.
    Uses extractive summarization (first few sentences + key sentences).
    """
    if not text or len(text) < 100:
        return text[:200]
    
    try:
        nlp = _get_nlp()
        if nlp is not None:
            doc = nlp(text[:5000])  # Limit to first 5000 chars for speed
            sentences = [sent.text.strip() for sent in doc.sents]
        else:
            # Lightweight sentence split fallback when spaCy is unavailable.
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text[:5000]) if s.strip()]
        
        if len(sentences) <= max_sentences:
            return " ".join(sentences)
        
        # Score sentences based on important keywords
        keywords = list(TOPIC_KEYWORDS.keys())
        keyword_list = []
        for kw_dict in TOPIC_KEYWORDS.values():
            keyword_list.extend(kw_dict["primary"])
            keyword_list.extend(kw_dict["secondary"])
        
        sentence_scores = {}
        for i, sent in enumerate(sentences):
            score = 0
            sent_lower = sent.lower()
            for kw in keyword_list:
                if kw in sent_lower:
                    score += 1
            sentence_scores[i] = score
        
        # Get top sentences
        top_indices = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:max_sentences]
        top_indices = sorted([idx for idx, _ in top_indices])
        
        summary = " ".join([sentences[i] for i in top_indices])
        return summary
    except Exception as e:
        # Fallback to first 300 chars
        return text[:300]


def fetch_news(days_back: int = 7, max_per_feed: int = 10):
    """
    Fetch and classify news articles.
    
    Args:
        days_back: Fetch news from last N days (0 = any date)
        max_per_feed: Max articles per feed
    """
    articles = []
    cutoff_date = datetime.utcnow() - timedelta(days=days_back) if days_back > 0 else None
    
    combined_feeds = RSS_FEEDS + TWITTER_RSS

    for feed_url in combined_feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:max_per_feed]:
                try:
                    # Extract and normalize date
                    pub_date_str = ""
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                        pub_date_str = pub_date.strftime("%Y-%m-%d")
                        if cutoff_date and pub_date < cutoff_date:
                            continue
                    else:
                        pub_date_str = datetime.utcnow().strftime("%Y-%m-%d")
                    
                    # Twitter/Nitter entries are short; skip heavyweight parsing to reduce failures
                    if "nitter.net" in feed_url:
                        text_content = entry.get("title", "") or entry.get("summary", "")
                        topics = classify_topics_nlp(text_content)
                        summary = extract_summary(text_content, max_sentences=2)
                        articles.append({
                            "id": str(uuid.uuid4()),
                            "title": entry.get("title", ""),
                            "text": text_content,
                            "summary": summary,
                            "topics": topics,
                            "source": feed_url,
                            "url": entry.get("link", ""),
                            "published": pub_date_str,
                            "date": pub_date_str,
                            "fetched_at": datetime.utcnow().isoformat()
                        })
                        continue

                    try:
                        article = Article(entry.link)
                        article.download()
                        article.parse()
                        
                        if not article.text or len(article.text.strip()) < 50:
                            continue
                        else:
                            topics = classify_topics_nlp(article.text)
                            summary = extract_summary(article.text, max_sentences=3)
                            
                            articles.append({
                                "id": str(uuid.uuid4()),
                                "title": article.title or entry.get("title", ""),
                                "text": article.text,
                                "summary": summary,
                                "topics": topics,
                                "source": feed_url,
                                "url": entry.link,
                                "published": pub_date_str,
                                "date": pub_date_str,
                                "fetched_at": datetime.utcnow().isoformat()
                            })
                    except Exception as e:
                        print(f"Failed to parse {entry.link}: {e}")
                except Exception:
                    pass
        except Exception:
            pass

    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    news_file = os.path.join(base_dir, "data", "news", "latest_news.json")
    
    with open(news_file, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2)

    print(f"Fetched {len(articles)} real news articles from last {days_back} days")
    return articles


def _fallback_extract(url: str) -> tuple[str, str]:
    """Try to extract title and text using requests + BeautifulSoup for robust parsing."""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        html = resp.text
        
        # Try BeautifulSoup for better HTML parsing
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title - try multiple methods
            title = None
            # Method 1: og:title
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title['content']
            # Method 2: regular title tag
            if not title and soup.title:
                title = soup.title.string
            # Method 3: h1 tag
            if not title:
                h1 = soup.find('h1')
                if h1:
                    title = h1.get_text()
            title = title or "Custom Article"
            
            # Extract text from multiple sources
            text_chunks = []
            
            # Try article/main content divs first
            for selector in ['article', 'main', '[role="main"]', '.article-content', '.post-content', '.story-content']:
                try:
                    content = soup.select_one(selector)
                    if content:
                        # Get all paragraphs
                        for p in content.find_all(['p', 'div', 'span']):
                            text = p.get_text(strip=True)
                            if text and len(text) > 20:
                                text_chunks.append(text)
                        if text_chunks:
                            break
                except:
                    pass
            
            # Fallback: Get all paragraphs from page
            if not text_chunks:
                for p in soup.find_all(['p', 'article']):
                    text = p.get_text(strip=True)
                    if text and len(text) > 30:
                        text_chunks.append(text)
            
            text = " ".join(text_chunks)
            if text:
                # Clean up whitespace
                text = re.sub(r'\s+', ' ', text).strip()
            
            return title, text
        
        except ImportError:
            # Fallback if BeautifulSoup not available - use simple regex
            # Title via og:title or <title>
            m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']', html, flags=re.I)
            title = m.group(1) if m else (re.search(r"<title>(.*?)</title>", html, flags=re.I|re.S).group(1) if re.search(r"<title>(.*?)</title>", html, flags=re.I|re.S) else "Custom Article")
            # Collect paragraph text
            paras = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.I|re.S)
            text_chunks = []
            for p in paras:
                cleaned = re.sub(r"<[^>]+>", "", p)
                cleaned = html_unescape.unescape(cleaned).strip()
                if cleaned and len(cleaned) > 30:
                    text_chunks.append(cleaned)
            text = " ".join(text_chunks)
            return title, text
    
    except Exception as e:
        from backend.logger import logger
        logger.warning(f"Fallback extraction failed: {str(e)[:100]}")
        return "Custom Article", ""


def add_custom_news(url: str, title: Optional[str] = None):
    """
    Add a custom news article from a given URL with proper error handling and timeouts.
    
    Args:
        url: URL of the article
        title: Optional custom title
        
    Returns:
        Article dictionary or None if failed
    """
    from backend.logger import logger
    
    try:
        logger.info(f"📥 Attempting to fetch article from: {url}")
        
        # Try newspaper3k with timeout
        try:
            article = Article(url, timeout=10)
            # Add headers to avoid being blocked
            article.http_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            article.download()
            article.parse()
            logger.info(f"✅ Successfully parsed article with newspaper3k")
        except Exception as e:
            logger.warning(f"⚠️ newspaper3k failed ({str(e)[:100]}), trying fallback...")
            parsed_title, parsed_text = _fallback_extract(url)
            if not parsed_text or len(parsed_text) < 100:
                logger.error(f"❌ Both newspaper3k and fallback failed for {url}")
                raise ValueError(f"Could not extract content from URL")
            article = None
        
        # Use newspaper3k results if available, otherwise use fallback
        if article:
            parsed_title = article.title or title or "Custom Article"
            parsed_text = article.text or ""
        else:
            # Already set from fallback
            parsed_title = title or parsed_title or "Custom Article"
        
        # Double fallback if text is too short
        if not parsed_text or len(parsed_text) < 300:
            logger.info("Text too short, trying enhanced fallback...")
            fb_title, fb_text = _fallback_extract(url)
            parsed_title = title or parsed_title or fb_title
            if fb_text and len(fb_text) > len(parsed_text):
                parsed_text = fb_text
        
        if not parsed_text or len(parsed_text) < 100:
            logger.error("Failed to extract meaningful content")
            return None
        
        logger.info(f"📊 Classifying topics and extracting summary...")
        topics = classify_topics_nlp(parsed_text)
        summary = extract_summary(parsed_text, max_sentences=3)
        
        article_dict = {
            "id": str(uuid.uuid4()),
            "title": parsed_title,
            "text": parsed_text,
            "summary": summary,
            "topics": topics,
            "source": "Custom User Input",
            "url": url,
            "published": "User provided",
            "fetched_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"💾 Saving article to news file...")
        # Append to existing news file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(script_dir)
        news_file = os.path.join(base_dir, "data", "news", "latest_news.json")
        
        try:
            with open(news_file, "r", encoding="utf-8") as f:
                articles = json.load(f)
        except Exception:
            articles = []
        
        articles.append(article_dict)
        
        with open(news_file, "w", encoding="utf-8") as f:
            json.dump(articles, f, indent=2)
        
        logger.info(f"✅ Successfully added custom article: {article_dict['title']}")
        return article_dict
        
    except Exception as e:
        from backend.logger import logger
        logger.error(f"❌ Failed to add custom news from {url}: {str(e)}", exc_info=True)
        return None


if __name__ == "__main__":
    # Fetch news from last 30 days with more articles per feed
    fetch_news(days_back=30, max_per_feed=20)
