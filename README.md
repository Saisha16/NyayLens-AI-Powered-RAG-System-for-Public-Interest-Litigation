# NyayLens - AI-Powered Public Interest Litigation Generator


>NyayLens is an end-to-end AI system that monitors public news sources, identifies potential public interest issues, maps them to constitutional rights and legal precedents, and generates structured **Public Interest Litigation (PIL) drafts** in a court-ready PDF format.

>This project focuses on **practical AI + system design**, not just models — combining NLP, semantic search, rule-based reasoning, and document generation.


## 🔍 Problem Statement

Public Interest Litigations often fail to be filed due to:
- Lack of legal awareness
- Manual effort in identifying constitutional violations
- Difficulty in mapping real-world events to relevant laws and precedents

NyayLens aims to **bridge the gap between news events and legal action** using AI.

---
## ✨ Key Features

- 📰 Automatic ingestion of news articles (RSS + URLs)
- 🧠 NLP-based entity extraction and issue classification
- ⚖️ Mapping issues to Fundamental Rights & legal domains
- 🔎 Semantic search over case laws using vector embeddings
- 🧾 Auto-generated PIL drafts (structured & editable)
- 📄 Court-ready PDF generation
- 🔐 Secure API with JWT authentication
- 🔄 Real-time status updates via WebSockets

---
## 🏗️ System Architecture

```
[ SOURCES ]          [ KNOWLEDGE ]
      News & URLs        Laws & Case Files
           │                    │
           ▼                    ▼
   ┌────────────────────────────────────┐
   │         PROCESSING ENGINE          │
   │  (Clean Text + Extract Keywords)   │
   └─────────────────┬──────────────────┘
                     │
           ┌─────────▼─────────┐
           │   LEGAL MAPPING   │
           │ (Score Severity & │
           │  Match to Rights) │
           └─────────┬─────────┘
                     │
           ┌─────────▼─────────┐
           │  PIL GENERATOR    │
           │ (Format to PDF)   │
           └─────────┬─────────┘
                     │
              [ FRONTEND UI ]
           Download & View Report

```

## 🧠 Technology Stack
---
| Component | Technology | Purpose |
|----------|-----------|---------|
| Backend API | FastAPI | Core application & API layer |
| NLP Engine | spaCy | Entity extraction & classification |
| News Ingestion | feedparser, newspaper3k | RSS parsing & article extraction |
| Semantic Search | FAISS / HNSW | Case law similarity search |
| Database | PostgreSQL | Persistent storage |
| PDF Engine | reportlab | Generate PIL documents |
| Authentication | JWT | Secure API access |
| Real-Time | WebSockets | Live status updates |
| Frontend | React / Vanilla JS | User interface |
| Testing | pytest | Unit & integration tests |

---


## 📂 Project Structure

---
```

pil26/
├── backend/
│   ├── main.py                      # FastAPI app with 13 endpoints
│   ├── ingest_news_enhanced.py      # News fetching, summarization, classification
│   ├── nlp_pipeline.py              # NER entity extraction
│   ├── rag_pipeline.py              # Constitutional references retrieval
│   ├── severity_scoring.py          # Weighted issue severity calculation
│   ├── pil_generator.py             # PIL document generation
│   ├── constitutional_db.py         # Legal database (rights, DPSPs, case laws)
│   ├── vector_store.py              # Vector embeddings for semantic search
│   ├── process_legal_docs.py        # Legal doc parsing
│   ├── db_models.py                 # SQLAlchemy ORM models 
│   ├── auth.py                      # JWT authentication 
│   ├── config.py                    # Configuration management 
│   ├── logger.py                    # Structured logging 
│   ├── validators.py                # Input validation 
│   └── tests/
│       ├── test_nlp_pipeline.py
│       ├── test_severity_scoring.py
│       ├── test_rag_pipeline.py
│       ├── test_main_endpoints.py
│       └── conftest.py
├── frontend/
│   ├── index.html
│   ├── app.js│  
│   └── style.css                       
├── data/
│   ├── news/latest_news.json
│   └── db.sqlite
├── requirements.txt
└── .env.example                    

```
---

## ⚙️ Installation & Setup
---
### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/nyaylens.git
cd nyaylens
```
2️⃣ Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```
3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```
4️⃣ Run Backend Server
```bash
uvicorn backend.api:app --reload
```
---
###🚀 Usage Flow

1. Submit a news URL or select an RSS feed

2. System extracts and analyzes the article

3. Relevant rights and legal domains are identified

4. Similar case laws are retrieved

5. A structured PIL draft is generated

6. Download the final PIL as a PDF
---

