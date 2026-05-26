# DocuSynth

DocuSynth is a Dockerized document intelligence platform with:

- FastAPI backend control plane
- FastAPI Python RAG service
- PostgreSQL + pgvector
- Redis caching and coordination
- Prometheus + Grafana observability
- Docker Compose local workflow

Legacy Go/Chi/C++/AVX2/SIMD/CGo components are inactive and archived. The active runtime stack is Python + FastAPI + PostgreSQL/pgvector + Redis.

## Architecture

- `backend` (FastAPI control plane): JWT auth, ingest proxy, query orchestration, Redis exact cache, pgvector semantic cache, multi-model council generation/review/synthesis, audit logs, Prometheus metrics.
- `python-rag` (FastAPI RAG service): PDF inspection/OCR/chunking, embedding generation, pgvector chunk retrieval.
- `postgres` (pgvector): stores users, documents, chunks, semantic cache entries, query logs, council responses, audit logs.
- `redis`: exact cache and rate-limit state.
- `prometheus` + `grafana`: metrics scraping and dashboards.

## Run

```bash
cp .env.example .env
docker compose up --build
```

DocuSynth maps Python-RAG to host port `8001` because `8000` is commonly used by other local apps.
Host mappings also use `5433` for PostgreSQL and `6380` for Redis to avoid common local conflicts.

## Ports

- backend: `localhost:8080` → container `8080`
- python-rag: `localhost:8001` → container `8000`
- postgres: `localhost:5433` → container `5432`
- redis: `localhost:6380` → container `6379`
- prometheus: `localhost:9091` → container `9090`
- grafana: `localhost:3000` → container `3000`

## Verify

```bash
curl http://localhost:8080/health
curl http://localhost:8080/metrics
curl http://localhost:8001/health
docker compose exec redis redis-cli ping
docker compose exec postgres psql -U docusynth -d docusynth -c "SELECT extname FROM pg_extension WHERE extname='vector';"
```

## Benchmark

### Mock mode

```bash
pip install -r tests/requirements-bench.txt
python tests/bench_semantic_cache.py --mock-llm
```

### Real mode

```bash
# backend environment must use MOCK_LLM=false and valid GEMINI_API_KEY/OPENROUTER_API_KEY
python tests/bench_semantic_cache.py
```

For local Ollama benchmarking, you can enable `LOCAL_LLM_FAST_MODE=true` to run
single-model fast mode (`single_local_fast`). This keeps the full multi-agent
council architecture available, but uses one local Ollama call per miss for
benchmark practicality on laptop hardware.

Benchmark outputs are generated locally in:

- `tests/benchmark_results_raw.json`
- `tests/benchmark_results.json`

If `--mock-llm` is used, results are explicitly mock-mode and are **not** resume-publishable performance numbers. Real resume-publishable metrics require `MOCK_LLM=false`, valid provider keys, enough samples, and no benchmark errors.

## Make Targets

```bash
make up
make down
make ps
make logs
make test
make bench-mock
make bench-real
make health
```
