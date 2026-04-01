#!/usr/bin/env python3
import json
from backend.severity_scoring import calculate_severity

# Load articles
with open('data/news/latest_news.json', 'r') as f:
    articles = json.load(f)

print('📊 Testing Severity Scoring with REAL articles:\n')
for i in range(min(5, len(articles))):
    article = articles[i]
    summary = article.get('summary', '')[:500]
    topics = article.get('topics', [])
    
    score = calculate_severity(summary)
    
    print(f'Article {i}: {article["title"][:50]}')
    print(f'  Topics: {topics}')
    print(f'  Severity Score: {score}')
    print(f'  Is Real?: {"✅ YES" if score != 0.5 else "❌ HARDCODED 0.5"}')
    print()
