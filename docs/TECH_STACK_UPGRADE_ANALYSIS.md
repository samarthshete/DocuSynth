# DocuSynth — Tech Stack Upgrade Analysis

> Honest fit assessment for each candidate technology against the **actual** architecture (two FastAPI services, pgvector, Redis, Streamlit, external LLM APIs, Docker Compose). No tech recommended for prestige. Compiled 2026-06-24.

Context anchors used throughout:
- LLM access is via **external HTTP APIs** (Ollama/Gemini/OpenRouter) — `backend/app/council/llm_client.py`. Nothing is trained or hosted in-repo.
- Orchestration today is a hand-written async function `run_council()` — `backend/app/council/orchestrator.py`.
- Data is **relational + vector**, single Postgres — `backend/app/db/models.py`, `services/python-rag/app/db.py`.
- Deployment is Docker Compose locally; cloud claim (Railway) is unverified — `docs/deployment.md`.

---

### LangChain
```
Should we add it? No (Maybe for a thin retrieval wrapper only)
Fit score: 3/10
Where it fits: could wrap the embed→retrieve→prompt chain in services/python-rag and backend/app/council.
Where it does NOT fit: the existing code is small, explicit, and already does exactly what LangChain abstracts (httpx calls, pgvector cosine, prompt assembly). Adding it hides logic reviewers want to see.
What feature it enables: faster swapping of retrievers/loaders — but you already have a clean provider abstraction.
Architecture change: replace bespoke retrieval/prompt code with LCEL chains; pulls in a large dependency tree.
Implementation difficulty: Medium.
Resume/interview value: Medium (common, not differentiating).
Risk of looking forced: High — it would obscure the custom semantic-cache logic that is your actual differentiator.
Final recommendation: Skip. Your hand-rolled pipeline is a stronger signal than "I imported LangChain." Keep the explicit code.
```

### LangGraph
```
Should we add it? Maybe (only if the multi-model council stays a headline feature)
Fit score: 6/10
Where it fits: the council is already a small state machine. Graph nodes map 1:1:
  - node "generate" -> council/generator.collect_candidates
  - node "review"   -> council/reviewer.review_candidates
  - node "chairman" -> council/synthesizer.synthesize
  - conditional edges -> the mode logic in orchestrator.run_council (single_local_fast / single_response / peer_review_no_chairman / full_council)
  - fallback edges -> the chairman-failure fallback already in orchestrator.py
Where it does NOT fit: the single_local_fast path (the benchmarked one) is a single call — a graph adds nothing there.
What feature it enables: explicit retries, per-node timeouts, circuit-breaking on a failing provider, and a visualizable agent graph (good demo artifact).
Architecture change: refactor council/orchestrator.py into a LangGraph StateGraph; keep generator/reviewer/synthesizer as node functions.
Implementation difficulty: Medium.
Resume/interview value: High ("modeled a multi-agent LLM workflow as a typed state graph with fallbacks").
Risk of looking forced: Medium — justified ONLY if you keep/feature the council; forced if you've de-emphasized it.
Final recommendation: Conditional. If the council survives the strategy in FUTURE_IMPLEMENTATION_STRATEGY.md as an optional mode, refactor it with LangGraph for the resume/interview story. Otherwise skip.
```

### Agent orchestration (generic)
```
Should we add it? No (beyond the LangGraph-of-the-council above)
Fit score: 3/10
Where it fits: nowhere new — there are no tools/agents to orchestrate; this is RAG, not an agent product.
Where it does NOT fit: adding tool-using agents would be scope creep away from the caching/retrieval thesis.
What feature it enables: nothing the product needs now.
Architecture change: large.
Implementation difficulty: High.
Resume/interview value: Medium but hollow without a real use case.
Risk of looking forced: High.
Final recommendation: Skip. Don't bolt on "agents" without a problem that needs them.
```

### Amazon EKS
```
Should we add it? No for MVP / Maybe for the production-grade story
Fit score: 4/10
Where it fits: a production-grade deploy of the (stateless) backend + python-rag with HPA, once there's real traffic.
Where it does NOT fit: current scale is single-node Docker Compose; EKS is heavy ops overhead for a demo.
What feature it enables: autoscaling, rolling deploys, multi-replica resilience.
Architecture change: Helm charts/K8s manifests; managed Postgres/Redis; ingress; secrets.
Implementation difficulty: High.
Resume/interview value: High for cloud/platform roles.
Risk of looking forced: High if done before CI/IaC basics exist.
Final recommendation: Defer to Phase 4. Do Terraform + a managed container deploy (ECS Fargate / Railway / Render) first; reach for EKS only to tell a deliberate "production-grade Kubernetes" story, and document why (HPA, multi-replica) — not for decoration.
```

### AWS Lambda
```
Should we add it? Maybe (narrow fit)
Fit score: 4/10
Where it fits: spiky, short async jobs — e.g., the document-ingest worker (OCR/embed) triggered off a queue, or scheduled cache-revalidation/eval runs.
Where it does NOT fit: the always-on FastAPI services (cold starts + the heavy torch/transformers image make Lambda awkward for embeddings).
What feature it enables: cheap event-driven ingest/eval without a running worker.
Architecture change: package the ingest worker as a container Lambda; SQS/EventBridge trigger.
Implementation difficulty: Medium (large ML image is the catch).
Resume/interview value: Medium-High (event-driven design).
Risk of looking forced: Medium — only sensible alongside the async-ingest-queue feature (F11).
Final recommendation: Maybe, paired with F11. Otherwise a normal worker process is simpler. Don't put the request-path API on Lambda.
```

### Amazon DynamoDB
```
Should we add it? No
Fit score: 2/10
Where it fits: arguably the Redis-style exact cache or audit logs (append-only, key access).
Where it does NOT fit: your core data is relational + vector (joins across users/documents/chunks, cosine search). pgvector + relational integrity is exactly right; DynamoDB has no vector search and would fragment the data model.
What feature it enables: nothing you lack — Redis already covers KV.
Architecture change: would split storage for no benefit.
Implementation difficulty: Medium.
Resume/interview value: Low here (wrong-tool signal to a senior reviewer).
Risk of looking forced: High.
Final recommendation: Skip. Relational + pgvector is the correct choice; say so in interviews. This is a good "I chose NOT to use DynamoDB because…" talking point.
```

### Amazon SageMaker
```
Should we add it? No
Fit score: 1/10
Where it fits: nowhere — you call external LLM APIs and use a pretrained HF embedding model. There is no training/fine-tuning workload.
Where it does NOT fit: everything; SageMaker solves training/hosting you don't do.
What feature it enables: none for the current product.
Architecture change: N/A.
Implementation difficulty: High.
Resume/interview value: Negative if unjustified (reviewers spot padding).
Risk of looking forced: Very High.
Final recommendation: Skip. If you ever self-host the embedding model for scale, a simple container (or SageMaker endpoint) could host it — but that's hypothetical. Don't add it now.
```

### Redis
```
Should we add it? Already in use — keep and extend
Fit score: 9/10
Where it fits: exact cache + rate-limit (existing), plus a job queue (F11) and SSE pub/sub if needed.
Where it does NOT fit: it should not be your durable store (it isn't).
What feature it enables: async ingest queue, sliding-window rate limiting (Lua), streaming fan-out.
Architecture change: minimal — add a queue library (rq/arq).
Implementation difficulty: Low.
Resume/interview value: Medium (well-used Redis is solid).
Risk of looking forced: None.
Final recommendation: Keep; extend for the async-ingest queue and fix the rate-limit implementation on top of it.
```

### Kafka or queue system
```
Should we add it? Queue: Yes (Redis-backed). Kafka: No.
Fit score: queue 7/10, Kafka 2/10
Where a queue fits: decouple ingest (OCR+embed) from the request path; retry failed ingests; schedule cache-revalidation/eval — F11.
Where Kafka does NOT fit: there is no high-throughput event-streaming/log use case; Kafka's ops cost is unjustified.
What feature it enables: async, retriable ingest; non-blocking uploads.
Architecture change: add rq/arq + a worker container; a job-status endpoint.
Implementation difficulty: Medium.
Resume/interview value: queue Medium-High; Kafka Low here.
Risk of looking forced: queue None; Kafka High.
Final recommendation: Add a Redis-backed queue (F11). Do NOT add Kafka — it would be the textbook "forced trendy tool."
```

### S3 or Cloudflare R2
```
Should we add it? Maybe (Yes once originals must be retained)
Fit score: 6/10
Where it fits: today uploaded bytes are processed in-memory and discarded (services/python-rag/app/routers/ingest.py). If you ever need re-processing, citations-to-original, or async ingest (worker reads the file later), object storage is the right place.
Where it does NOT fit: not needed for the current in-memory, synchronous ingest.
What feature it enables: durable originals, re-ingest without re-upload, async worker handoff.
Architecture change: store upload to S3/R2 in the ingest proxy; worker reads from it.
Implementation difficulty: Low-Medium.
Resume/interview value: Medium.
Risk of looking forced: Low — natural once F11 (async ingest) exists.
Final recommendation: Add together with F11/async ingest. Not before.
```

### OpenTelemetry
```
Should we add it? Yes
Fit score: 9/10
Where it fits: trace a request across backend -> python-rag (embed, retrieve) -> Postgres -> LLM provider, with spans per stage. You already compute a timings dict in query.py — OTel makes it real distributed tracing.
Where it does NOT fit: nowhere problematic.
What feature it enables: end-to-end latency attribution, debugging cross-service slowness, a strong platform demo (Tempo/Jaeger).
Architecture change: add opentelemetry SDK + FastAPI/httpx/SQLAlchemy instrumentation in both main.py; propagate context over the backend->rag HTTP hop; export to an OTel collector.
Implementation difficulty: Medium.
Resume/interview value: High (distributed tracing across microservices).
Risk of looking forced: Low — it directly upgrades your existing instrumentation.
Final recommendation: Add (F6). High signal, natural fit, pairs with the existing Prometheus setup.
```

### Prometheus / Grafana
```
Should we add it? Already in use — extend
Fit score: 9/10
Where it fits: metrics (existing). Extend to scrape the RAG service (currently NOT scraped — monitoring/prometheus.yml targets backend only) and add token/cost + cache-quality panels.
Where it does NOT fit: it's metrics, not tracing — pair with OTel, don't conflate.
What feature it enables: live cache hit-rate, cost-saved, p95-by-cache_result dashboards.
Architecture change: add /metrics to python-rag; add a scrape job; new Grafana panels.
Implementation difficulty: Low.
Resume/interview value: Medium-High.
Risk of looking forced: None.
Final recommendation: Keep; scrape the RAG service; build the cost + cache-quality dashboards (ties to F7/F1).
```

### Terraform
```
Should we add it? Yes
Fit score: 8/10
Where it fits: provision managed Postgres(pgvector) + Redis + the container services + secrets for a reproducible cloud deploy; replaces the unverified manual Railway steps in docs/deployment.md.
Where it does NOT fit: not needed for purely-local Compose dev.
What feature it enables: one-command, reviewable, reproducible infrastructure; a real IaC artifact.
Architecture change: a terraform/ module targeting your chosen platform (AWS ECS/Fargate, or Railway/Render providers).
Implementation difficulty: Medium.
Resume/interview value: High (IaC is a core platform signal).
Risk of looking forced: Low.
Final recommendation: Add (F12). Strong cloud signal and it fixes the credibility gap around deployment.
```

### GitHub Actions CI/CD
```
Should we add it? Yes — do this first
Fit score: 10/10
Where it fits: run ruff + mypy + pytest + build both images + a MOCK_LLM smoke on every PR; later, push images + terraform plan.
Where it does NOT fit: nowhere problematic.
What feature it enables: every other change becomes safe; PR badge; reproducibility.
Architecture change: .github/workflows/ci.yml + lint/type config.
Implementation difficulty: Low.
Resume/interview value: High (table stakes; its absence is a red flag).
Risk of looking forced: None.
Final recommendation: Add immediately (F4). Cheapest highest-trust upgrade in the whole list.
```

---

## Summary verdict

| Add now | Add soon (justified) | Skip / avoid |
|---|---|---|
| GitHub Actions CI/CD, OpenTelemetry, extend Prometheus/Grafana, Terraform, keep+extend Redis | Redis-backed queue + async ingest (F11), S3/R2 (with F11), LangGraph (only if council stays), Lambda (only with F11), EKS (Phase 4 production story) | LangChain, generic agents, DynamoDB, SageMaker, Kafka |

**One-line rule:** add tools that deepen *retrieval quality, correctness, observability, and reproducible deployment* — the project's real axes. Reject tools that imply workloads DocuSynth doesn't have (training → SageMaker, event streaming → Kafka, KV-at-scale-without-vectors → DynamoDB).
