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

- 📰 **Automatic news ingestion** from 14+ RSS feeds (legal, mainstream, investigative sources)
- 🗓️ **Flexible date filtering** - Filter by year, month, specific date, or date range
- 🧠 **NLP-based entity extraction** and intelligent issue classification
- ⚖️ **Constitutional mapping** - Links issues to Fundamental Rights & legal domains
- 🔎 **Semantic search** over 1,064 legal documents using vector embeddings
- 🧾 **Auto-generated PIL drafts** - Structured, editable court documents
- 📄 **Court-ready PDF generation** with proper legal citations
- 🔐 **Secure JWT authentication** for API access
- 🤖 **AI explainability** - Transparent reasoning for severity scoring and legal grounds
- ⏰ **Automated scheduling** - Daily news updates at 08:00
- 📝 **Custom article input** - Add articles from URLs or direct text

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
## 1️⃣ Clone the Repository
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
## 🚀 Usage Flow
1. **Input:** Submit a news URL or select a pre-configured RSS feed.
2. **Extraction:** The system extracts and analyzes the article content.
3. **Classification:** Relevant rights and legal domains are identified.
4. **Retrieval:** Similar case laws and constitutional precedents are retrieved via RAG.
5. **Generation:** A structured PIL draft is synthesized based on legal formatting.
6. **Export:** Download the final PIL as a formatted PDF.

---

## 🧪 Testing

To run the test suite, execute:

```bash
pytest
```
---
## 📌 Example Use Cases

* **Legal Aid Organizations:** Streamlining the drafting of grievances for underserved communities.
* **Law Students & Researchers:** Accelerating the process of linking news events to legal precedents.
* **NGOs:** Efficiently monitoring and documenting large-scale public rights violations.
* **Journalists & Civic-Tech Platforms:** Providing a direct bridge between investigative reporting and legal action.
---
## 🎯 What This Project Demonstrates

* **End-to-End AI System Design:** A complete pipeline from raw data ingestion to structured document generation.
* **Real-World NLP Application:** Practical implementation of Named Entity Recognition (NER), semantic search, and RAG for domain-specific tasks.
* **Full-Stack Integration:** Seamless communication between a robust Python backend and a reactive frontend UI.
* **Legal-Tech Domain Understanding:** Direct mapping of current events to Constitutional Articles, DPSPs, and Landmark Case Laws.
* **Clean & Scalable Architecture:** A modular codebase built with industry-standard patterns, ensuring maintainability and ease of testing.
---
## 📜 Disclaimer

This project is for educational and research purposes only. Generated PIL drafts are preliminary templates and **must be reviewed by qualified legal professionals** before any formal use or filing.

---

## 👩‍💻 Author

**Isha Sahay** 
*AI / Full-Stack Developer* Focused on building real-world, impact-driven systems.
