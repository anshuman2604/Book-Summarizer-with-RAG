# AI Agentic Book Summarizer & Q&A Engine

An intelligent, multi-tenant RAG application capable of ingesting massive 500+ page books (PDF/DOCX), producing strict ~100-word executive summaries, and answering specific questions with exact page number citations and KaTeX scientific formula rendering.

---

## Key Features

- **Massive Document Support (500+ Pages):** Powered by PyMuPDF (compiled C engine) for near-instant text extraction.
- **RAG Agent with Strict Grounding:** Semantic retrieval over PostgreSQL `pgvector` using cosine similarity (`<=>`). All claims are cited with `[Page X]` stamps.
- **100-Word Executive Summary:** Distills whole books using equidistant macro-sampling and single-call LLM synthesis.
- **Multi-Tenant Authentication & Session History:** Secure JWT authentication with user-isolated book history and chat persistence.
- **Production-Ready Modularity:** Clean separation between FastAPI backend, Supabase pgvector database, and Next.js 14 frontend.

---

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | Next.js 14 (App Router), React 18, Tailwind CSS, Lucide Icons, KaTeX, React-Markdown |
| **Backend** | FastAPI, Uvicorn, Pydantic v2, SQLAlchemy |
| **Database** | Supabase PostgreSQL with `pgvector` extension |
| **Embeddings** | Cohere `embed-english-v3.0` (1024 dimensions) |
| **LLM Inference** | Google Gemini 2.5 Flash via official `google-genai` SDK |
| **PDF Extraction**| PyMuPDF (`fitz`) with fallback to `pypdf` |

---

## Documentation

- **[Architecture & Design Document](ARCHITECTURE.md):** In-depth breakdown of the ingestion pipeline, RAG retrieval mechanism, and database schemas.
- **[REST API Documentation](API_DOCUMENTATION.md):** Complete specification of all endpoints, request/response formats, and HTTP status codes.
- **[Concepts & Explanations](EXPLANATIONS.md):** Plain-language explanation of vector search, cosine distance, JWTs, and chunking strategies.

---

## Getting Started (Local Setup)

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- A Supabase PostgreSQL project with `pgvector` enabled
- API Keys: Google Gemini API Key & Cohere API Key

### 2. Backend Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd "Book summarizer"

# Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env in root directory
# Required environment variables:
# DATABASE_URL=postgresql://postgres.xxx:password@aws-0-region.pooler.supabase.com:6543/postgres
# SECRET_KEY=your_random_secret_key_here
# GEMINI_API_KEY=your_gemini_api_key
# COHERE_API_KEY=your_cohere_api_key

# Run FastAPI backend server
uvicorn backend.main:app --reload --port 8000
```
Swagger documentation will be available at `http://localhost:8000/docs`.

### 3. Frontend Setup
```bash
cd frontend

# Install packages
npm install

# Run Next.js development server
npm run dev -p 3000
```
Open `http://localhost:3000` in your browser.

---
