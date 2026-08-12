# AI Document Analyzer

LLM-powered document analysis API with semantic search and conversational Q&A.

Upload documents, get intelligent summaries, and chat with your files using natural language.

## Features

- **Document Ingestion** — Read and retain PDF, DOCX, DOC, TXT, and Markdown files
- **AI Summarization** — Generate summaries and extract key points using Pydantic AI
- **Semantic Search** — Find relevant content across documents using vector embeddings
- **Conversational Q&A** — Ask questions about your documents with RAG-powered responses

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Python 3.14+ |
| **Frontend** | HTMX, Tailwind CSS CDN |
| **AI/LLM** | Pydantic AI with OpenAI |
| **Embeddings** | OpenAI `text-embedding-3-small` |
| **Vector Store** | ChromaDB |
| **Document Parsing** | pdfreader, pypdfium2, RapidOCR, python-docx, LibreOffice |
| **DevOps** | Docker, GitHub Actions |

## Quick Start

### Prerequisites

- Python 3.14+
- [UV](https://docs.astral.sh/uv/) package manager
- OpenAI API key

### Installation

```bash
git clone https://github.com/krytos/ai-document-analyzer.git
cd ai-document-analyzer

uv sync --locked --all-groups

cp .env.example .env

uv run uvicorn document_analyzer.main:app --reload
```

### Chat from the terminal

```bash
uv run ai-document-analyzer chat
```

The CLI reads and indexes the retained sample PDF, then accepts questions until
`exit` or `quit` is entered. Use `summary` as a shortcut for a document summary.
Chat responses are returned after generation; token streaming is not currently enabled.

Open [http://localhost:8000](http://localhost:8000) in your browser.

### Docker

```bash
docker compose up -d --build
```

The application is available at [http://localhost:8000](http://localhost:8000).
SQLite, ChromaDB, uploaded originals, and logs are persisted in the named
`document_data` volume. To run the live-reloading development service instead:

```bash
docker compose --profile dev up --build development
```

The development service is available at [http://localhost:8001](http://localhost:8001)
and mounts `src/` into the container.

## Usage

### Analyze the sample document

The current backend intentionally uses `src/document_analyzer/core/sample.pdf`.
Uploaded originals and their extracted text are retained for later analysis.

```bash
curl -X POST "http://localhost:8000/api/documents/sample/ingest"

curl -X POST "http://localhost:8000/api/documents/sample/summary"

curl -X POST "http://localhost:8000/api/documents/sample/question" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main findings?"}'
```

Set `OPENAI_API_KEY` in `.env` before using the embedding or analysis endpoints.
Chroma data is persisted under `.data/chroma` by default.

### Web upload workspace

The web interface at `/` accepts PDF, DOCX, DOC, TXT, and Markdown files. Uploads
are retained, indexed in ChromaDB, and opened in the HTMX analysis workspace.
Summaries are generated lazily from the chat suggestions. Legacy `.doc` files
require the bundled headless LibreOffice runtime. Image-only PDF files are
rendered and OCR'd with the Python dependencies installed by `uv`; no separate
OCR runtime is required.

## Project Structure

```
src/document_analyzer/
├── main.py
├── api/routes/
├── core/
├── services/
├── models/
└── templates/
```

## Architecture

```
Upload → Parse → Chunk → Embed → Store (ChromaDB)
                                      ↓
Query → Embed Question → Semantic Search → LLM + Context → Response
```

## Development

```bash
uv run pytest

uv run ty check

uv run ruff check src tests

uv run ruff format --check src tests
```

CI runs Ruff linting and formatting checks, Ty, pytest with coverage reporting,
and a Docker runtime image build for pull requests and pushes to `main`.

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
