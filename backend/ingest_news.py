import feedparser
from newspaper import Article
import uuid
import json
from datetime import datetime
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
except (ImportError, OSError):
    spacy = None
    nlp = None
from collections import Counter

# Enhanced topic keyword mapping with weights
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

RSS_FEEDS = [
    "https://feeds.feedburner.com/ndtvnews-top-stories",
    "https://www.thehindu.com/news/national/feeder/default.rss",
    "https://indianexpress.com/section/india/feed/"
]


def classify_topics_nlp(text: str):
    """
    Use NLP-based topic classification:
    1. Weighted keyword matching (primary keywords = 2 points, secondary = 1 point)
    2. Named entity recognition for context
    3. Multi-label classification (article can have multiple topics)
    """
    doc = nlp(text.lower())
    text_lower = text.lower()
    
    # Score each topic
    topic_scores = {}
    
    for topic, keyword_groups in TOPIC_KEYWORDS.items():
        score = 0
        
        # Primary keywords (higher weight)
        for kw in keyword_groups["primary"]:
            if kw in text_lower:
                score += 2
        
        # Secondary keywords (lower weight)
        for kw in keyword_groups["secondary"]:
            if kw in text_lower:
                score += 1
        
        if score > 0:
            topic_scores[topic] = score
    
    # Extract entities for additional context
    entities = [ent.text.lower() for ent in doc.ents if ent.label_ in ["ORG", "GPE", "LAW", "EVENT"]]
    
    # Boost scores based on entity context
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
    
    # Return topics with score >= 2 (threshold for relevance)
    selected_topics = [topic for topic, score in topic_scores.items() if score >= 2]
    
    return selected_topics if selected_topics else ["general"]


def fetch_news():
    articles = []
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:10]:
            try:
                article = Article(entry.link)
                article.download()
                article.parse()
                topics = classify_topics_nlp(article.text)
                articles.append({
                    "id": str(uuid.uuid4()),
                    "title": article.title,
                    "text": article.text,
                    "topics": topics,
                    "source": feed_url,
                    "published": str(entry.get("published", "")),
                    "fetched_at": datetime.utcnow().isoformat()
                })
            except Exception:
                continue

    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    news_file = os.path.join(base_dir, "data", "news", "latest_news.json")
    
    with open(news_file, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2)

    print(f"Fetched {len(articles)} real news articles")


if __name__ == "__main__":
    fetch_news()
