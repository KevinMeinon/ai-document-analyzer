# AI Document Analyzer

LLM-powered document analysis API with semantic search and conversational Q&A.

Upload documents, get intelligent summaries, and chat with your files using natural language.

## Features

- **Document Ingestion** — Read and retain PDF, DOCX, DOC, TXT, and Markdown files
- **AI Summarization** — Generate summaries and extract key points using Pydantic AI
- **Semantic Search** — Find relevant content across documents using vector embeddings
- **Conversational Q&A** — Ask questions about your documents with RAG-powered responses
- **Streaming Responses** — Real-time LLM output via Server-Sent Events

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Python 3.12+ |
| **Frontend** | HTMX, Tailwind CSS CDN |
| **AI/LLM** | Pydantic AI with OpenAI |
| **Embeddings** | OpenAI `text-embedding-3-small` |
| **Vector Store** | ChromaDB |
| **Document Parsing** | pdfreader, python-docx, LibreOffice |
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

### Chat from the terminal

```bash
uv run ai-document-analyzer chat
```

The CLI reads and indexes the retained sample PDF, then accepts questions until
`exit` or `quit` is entered. Use `summary` as a shortcut for a document summary.

Open [http://localhost:8000](http://localhost:8000) in your browser.

### Docker

```bash
docker-compose up -d
```

## Usage

### Analyze the sample document

The current backend intentionally uses `src/document_analyzer/core/sample.pdf`.
The PDF remains on disk and is re-read whenever analysis is requested.

```bash
# Index or refresh the sample PDF in persistent ChromaDB
curl -X POST "http://localhost:8000/api/documents/sample/ingest"

# Generate a summary
curl -X POST "http://localhost:8000/api/documents/sample/summary"

# Ask a question
curl -X POST "http://localhost:8000/api/documents/sample/question" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main findings?"}'
```

Set `OPENAI_API_KEY` in `.env` before using the embedding or analysis endpoints.
Chroma data is persisted under `.data/chroma` by default.

### Web upload workspace

The web interface at `/` accepts PDF, DOCX, DOC, TXT, and Markdown files. Uploads
are retained under `.data/uploads`, indexed in ChromaDB, summarized synchronously,
and opened in the HTMX analysis workspace. Legacy `.doc` files require the
headless `soffice` executable.

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
