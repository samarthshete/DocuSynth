# DocuSynth

DocuSynth is a Dockerized RAG document intelligence platform for local PDF ingestion, semantic retrieval, caching, local LLM answering, and observability.

It is designed as a backend-focused portfolio project: multiple services, explicit data stores, reproducible Docker Compose setup, metrics, and a benchmark harness for cache and retrieval behavior.

## What It Solves

Document QA systems are often hard to reason about once retrieval, caching, LLM calls, and metrics are split across services. DocuSynth makes that flow explicit: ingest a PDF, chunk and store it, retrieve relevant context, serve an answer, cache repeat work, and expose operational metrics.

## Key Features

- PDF ingestion through a FastAPI backend.
- Dedicated Python RAG service for document chunking and retrieval.
- PostgreSQL with pgvector for document chunks and semantic lookup.
- Redis for exact query caching and rate-limit state.
- Local Ollama model support for local answer generation.
- Streamlit UI for interactive demo use.
- Prometheus and Grafana for backend, cache, retrieval, and LLM metrics.
- Docker Compose setup for repeatable local infrastructure.
- Benchmark script for semantic-cache and latency experiments.

## Tech Stack

| Area | Technology |
|---|---|
| Backend API | FastAPI, Python |
| RAG service | Python, embeddings, PDF processing |
| Data | PostgreSQL, pgvector |
| Cache | Redis |
| LLM runtime | Ollama local model mode, optional hosted provider configuration |
| UI | Streamlit |
| Observability | Prometheus, Grafana |
| DevOps | Docker Compose, Makefile |

## Architecture

```text
PDF / Query
   |
   v
FastAPI backend  ---- metrics ----> Prometheus ----> Grafana
   |
   +---- Redis exact cache / rate limit state
   |
   +---- Python RAG service ----> PostgreSQL + pgvector
   |
   +---- Local LLM provider for answer generation
   |
   v
Streamlit demo UI
```

Request flow for `POST /api/v1/query`:

1. Authenticate and rate-limit the request.
2. Check Redis for an exact cache hit.
3. Embed the query and check semantic cache/vector similarity paths.
4. Retrieve relevant chunks from the RAG service on cache miss.
5. Generate an answer with the configured LLM provider.
6. Store cache artifacts and emit metrics.

## Project Structure

```text
DocuSynth/
|-- backend/                 # FastAPI control plane
|-- services/python-rag/      # RAG service for chunking and retrieval
|-- streamlit/app.py          # Demo UI
|-- monitoring/               # Prometheus and Grafana config
|-- scripts/                  # Smoke checks
|-- tests/                    # Benchmark and test assets
|-- docs/images/              # README images and diagrams
|-- docker-compose.yml
|-- Makefile
`-- README.md
```

## Environment Variables

Copy `.env.example` to `.env` and fill in local values. Keep secrets out of commits.

Common variables:

```env
DATABASE_URL=postgresql+psycopg://<db_user>:<db_password>@postgres:5432/<db_name>
REDIS_URL=redis://redis:6379/0
JWT_SECRET=replace_with_long_random_string
LLM_PROVIDER=ollama
LOCAL_LLM_FAST_MODE=true
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1/chat/completions
OLLAMA_MODEL=qwen2.5:3b
GEMINI_API_KEY=
OPENROUTER_API_KEY=
```

## Run Locally

Prerequisites:

- Docker and Docker Compose
- Python 3 for local scripts
- Ollama if using local model mode

```bash
ollama pull qwen2.5:3b
cp .env.example .env
make up
make health
make streamlit
```

Useful URLs:

- Streamlit UI: http://localhost:8501
- Backend health: http://localhost:8080/health
- RAG service health: http://localhost:8001/health
- Prometheus: http://localhost:9091
- Grafana: http://localhost:3000

## API Examples

Login:

```bash
curl -s -X POST http://localhost:8080/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo123"}'
```

Ingest a PDF:

```bash
TOKEN="<jwt-token>"
curl -s -X POST http://localhost:8080/api/v1/ingest \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "file=@tests/fixtures/sample.pdf"
```

Query a document:

```bash
TOKEN="<jwt-token>"
DOC_ID="<doc-id>"
curl -s -X POST http://localhost:8080/api/v1/query \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"doc_id\":\"${DOC_ID}\",\"question\":\"Summarize the key ideas\",\"top_k\":5}"
```

## Testing And Benchmarking

```bash
make test
make smoke
make benchmark
```

The benchmark harness is intended for local comparison of cache behavior and latency paths. Treat results as environment-specific unless reproduced on the same hardware and configuration.

## Deployment Notes

The repository supports local Docker Compose operation. A lightweight Streamlit-only demo path is documented in the existing app files, but the full multi-service platform requires provisioned Postgres, Redis, metrics, and an LLM provider endpoint.

## Security Notes

- Do not commit `.env` files.
- Use placeholders in `.env.example` only.
- Rotate any credential that was ever exposed in logs or history.

## Future Improvements

- Add cloud deployment templates for managed Postgres and Redis.
- Add token refresh for long benchmark sessions.
- Expand benchmark reports with reproducibility metadata.
- Add more integration tests for cache decision paths.

## License

See repository license files if present.
