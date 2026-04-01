# AI Document Analyzer

LLM-powered document analysis API with semantic search and conversational Q&A.

Upload documents, get intelligent summaries, and chat with your files using natural language.

## Features

- **Document Ingestion** — Upload PDF/DOCX files with automatic text extraction
- **AI Summarization** — Generate summaries and extract key points using GPT-4/Claude
- **Semantic Search** — Find relevant content across documents using vector embeddings
- **Conversational Q&A** — Ask questions about your documents with RAG-powered responses
- **Streaming Responses** — Real-time LLM output via Server-Sent Events

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Python 3.12+ |
| **Frontend** | HTMX, Bulma CSS |
| **AI/LLM** | OpenAI GPT-4 / Anthropic Claude |
| **Embeddings** | sentence-transformers / OpenAI |
| **Vector Store** | ChromaDB |
| **Document Parsing** | pypdf, python-docx |
| **DevOps** | Docker, GitHub Actions |

## Quick Start

### Prerequisites

- Python 3.12+
- [UV](https://docs.astral.sh/uv/) package manager
- OpenAI or Anthropic API key

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/ai-document-analyzer.git
cd ai-document-analyzer

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run development server
uv run uvicorn document_analyzer.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### Docker

```bash
docker-compose up -d
```

## Usage

### Upload a Document

```bash
curl -X POST "http://localhost:8000/api/documents/upload" \
  -F "file=@document.pdf"
```

### Analyze a Document

```bash
curl "http://localhost:8000/api/documents/{doc_id}/analyze"
```

### Chat with Documents

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"document_ids": ["doc_id"], "question": "What are the main findings?"}'
```

## Project Structure

```
src/document_analyzer/
├── main.py              # FastAPI application
├── config.py            # Settings management
├── api/routes/          # HTTP endpoints
├── core/                # Document parsing, embeddings, LLM
├── services/            # Business logic
├── models/              # Pydantic schemas
└── templates/           # HTMX frontend
```

## Architecture

```
Upload → Parse → Chunk → Embed → Store (ChromaDB)
                                      ↓
Query → Embed Question → Semantic Search → LLM + Context → Response
```

## Development

```bash
# Run tests
uv run pytest

# Type checking
uv run ty

# Linting
uv run ruff check src/

# Format code
uv run ruff format src/
```

## Business Value

This project demonstrates production-ready AI integration patterns:

- **Document Automation** — Reduce manual document review time
- **Knowledge Retrieval** — Enable natural language queries across document collections
- **Scalable Architecture** — Handle thousands of documents with vector search

## License

MIT

## Author

**Kevin Meinon**  
Python Backend Developer | AI Integration & Cloud Automation

📧 kevin@meinon.de