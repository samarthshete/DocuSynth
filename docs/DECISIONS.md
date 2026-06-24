# DocuSynth — Decision Log (ADR-style)

> Decisions inferred from the code (no ADRs existed in the repo), the likely rationale, a candid assessment, and better alternatives where the current choice is weak. Plus decisions still pending. Compiled 2026-06-24.

Each entry: **Decision → Evidence → Likely rationale → Assessment → Better alternative (if any).**

---

## D1. Microservice split: control plane (`backend/`) + RAG service (`python-rag/`)
- **Evidence:** two FastAPI apps, `RAG_SERVICE_URL`, HTTP calls in `backend/app/rag/{embeddings,retrieval}.py`.
- **Rationale:** isolate heavy ML deps (torch/transformers/OCR) from the lightweight control plane; scale embedding/retrieval independently.
- **Assessment:** Reasonable, but the boundary leaks — the backend reads/writes the same `chunks`/Postgres the RAG service owns, and both define ORM models and run `create_all`. The split's value is partly undone.
- **Better:** Make Postgres the RAG service's private store; have the backend reach chunks only via RAG APIs. Or merge into one service if scale doesn't justify two. Adopt one schema source (Alembic).

## D2. Python rewrite; Go backend archived
- **Evidence:** `services/go-backend/ARCHIVED.md`; Go not in compose; Python `backend/` active.
- **Rationale:** Python's ML/RAG ecosystem (transformers, pdfplumber, pytesseract) is far richer; single-language stack is simpler.
- **Assessment:** Sound. But the Go/C++ tree (incl. a native semantic cache) is still committed — dead weight and confusion.
- **Better:** Delete the Go backend (it lives in git history) or move to a clearly separate `archive/` branch.

## D3. Two-tier cache: Redis exact + pgvector semantic
- **Evidence:** `cache/redis_cache.py`, `cache/semantic_cache.py`, cascade in `api/query.py`.
- **Rationale:** exact cache is O(1) cheap; semantic cache captures paraphrases to cut LLM calls — the project's headline feature.
- **Assessment:** Good idea, genuinely differentiating. **But** the semantic cache (a) never invalidates on document change, (b) never evicts, (c) keys only on (doc_id, query embedding) — not on retrieved context.
- **Better:** Store a document content-hash with each cache row and invalidate on re-ingest; add TTL/LRU; consider keying on the retrieved-chunk set so answers track the actual context.

## D4. Vector store = pgvector inside the primary Postgres
- **Evidence:** `vector(384)` columns; `cosine_distance` ordering.
- **Rationale:** one datastore for relational + vector data; no extra infra; pgvector is production-capable.
- **Assessment:** Great for a demo. **No ANN index** → exact scans; this is the first real scaling wall.
- **Better:** Add an HNSW index (`vector_cosine_ops`) on `chunks.embedding` and `semantic_cache.embedding`. At larger scale, evaluate a dedicated vector DB only if pgvector+HNSW is insufficient.

## D5. Local transformer embeddings (`BAAI/bge-small-en-v1.5`, 384-dim, mean pooling)
- **Evidence:** `embedding/transformer.py` (raw `transformers` + mean pooling), config default.
- **Rationale:** free, offline, small (384-dim keeps vectors light).
- **Assessment:** Works, but bge models expect a query-instruction prefix and normalized embeddings; generic mean pooling without normalization likely costs retrieval quality. Also `sentence-transformers` is installed but unused.
- **Better:** Use `sentence-transformers` with the model's recommended pooling/normalization, or add the bge query prefix + L2-normalize before cosine.

## D6. Multi-model "council" (generate → peer review → chairman) + a fast single path
- **Evidence:** `council/{orchestrator,generator,reviewer,synthesizer}.py`; modes incl. `single_local_fast`.
- **Rationale:** ensemble + critique can raise answer quality; the fast path exists for cheap/offline benchmarking.
- **Assessment:** Interesting and distinctive, but **full council = up to 7 LLM calls/query** (3 generate + 3 review + 1 chairman) — expensive and latency-heavy, and depends on brittle "free"/forward-dated model ids. The benchmarked numbers come from the *single* path, not the council, which slightly oversells the multi-model angle.
- **Better:** Make the council opt-in per request; cap members; circuit-break slow/failing providers; benchmark the council mode explicitly and report it separately.

## D7. LLM provider abstraction via env flags (Ollama / Gemini / OpenRouter)
- **Evidence:** `council/llm_client.py`, `config.py`, `.env.example` modes A/B.
- **Rationale:** same code runs offline (Ollama) or cloud (Gemini) by config — strong portability story.
- **Assessment:** Good. Weakness: model ids are hardcoded defaults (some forward-dated), and Gemini is integrated by raw REST here but via SDK in the cloud demo (two styles).
- **Better:** Centralize provider/model config with validation; verify ids against live APIs; unify Gemini integration.

## D8. JWT (HS256) + bcrypt; demo user auto-seeded
- **Evidence:** `auth/jwt.py`, `auth/security.py`, seed in `main.py`.
- **Rationale:** simplest stateless auth for a demo; seed user enables instant try-out + benchmarks.
- **Assessment:** Fine for a demo. Risks for anything beyond: no refresh/rotation/revocation, `iss` unverified, open self-registration, auto-seeded `demo/demo123`.
- **Better:** Verify `iss`/`aud`; add refresh + revocation; gate `/register`; disable demo seed outside dev; move admin endpoints behind a role.

## D9. Streamlit for UI; separate standalone cloud demo
- **Evidence:** `streamlit/app.py`; `streamlit_cloud_app.py` (keyword retrieval + optional Gemini).
- **Rationale:** fastest way to a usable UI; the standalone demo gives a zero-cost public showcase without the Docker stack.
- **Assessment:** Pragmatic. The cloud demo's keyword (token-overlap) retrieval is much weaker than the real pgvector path — acceptable if clearly labeled (it is).
- **Better:** If a product frontend is desired, a real SPA + the backend API. Otherwise keep Streamlit.

## D10. Rate limiting via Redis fixed-window counter, fail-open
- **Evidence:** `redis_cache.py:56-65` — `count <= rps*window`.
- **Rationale:** trivial to implement; avoids blocking users if Redis hiccups.
- **Assessment:** **Weak.** The math allows ~300 req/min (not "5 rps"), it's a coarse fixed window (burst at boundaries), and it fails open (no protection during Redis outage).
- **Better:** Sliding-window or token-bucket (Redis Lua), correct units, explicit fail-open/closed policy, per-route limits.

## D11. Schema via init SQL + `create_all` (no migrations)
- **Evidence:** `migrations_or_init.sql` mounted into Postgres + `Base.metadata.create_all()` in both services.
- **Rationale:** least friction to stand up a fresh DB.
- **Assessment:** Fragile; three sources of truth can drift; no versioned change path; `council_responses` exists but is unused.
- **Better:** Alembic with a single ORM source; drop unused tables.

## D12. Default `MOCK_LLM=true`
- **Evidence:** `config.py:14`, `docker-compose.yml:16`.
- **Rationale:** lets tests and first-run demos work without any API key/Ollama.
- **Assessment:** Confusing for new users (real-looking but mock answers).
- **Better:** Default to a clearly labeled mock *with a startup banner*, or default to Ollama and document the prerequisite; tests can set the env explicitly.

---

## Pending Decisions (need an owner's call)

1. **Project intent:** portfolio/reference artifact vs. real deployable product? (Drives everything in `ROADMAP.md`.)
2. **Is the council the production path** or is single-model (Ollama/Gemini) the target? Benchmark and document the chosen one honestly.
3. **Multi-tenancy:** enforce per-user document isolation, or formally declare single-tenant demo?
4. **Cloud hosting:** keep Railway, verify/remove the live URLs, or drop cloud claims?
5. **Embedding model & dimension:** standardize on one model + correct pooling; confirm 384-dim everywhere.
6. **Authoritative benchmark:** which run, which mode, regenerated by whom, on what hardware?
7. **Branding:** finish the CouncilAI→DocuSynth rename (metrics vars, JWT iss, Go module) or leave history alone.
