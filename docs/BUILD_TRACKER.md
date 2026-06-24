# DocuSynth — Build Tracker

> **Single source of truth for build progress.** Update this file at the end of every work item and every session.
> Full plan: `IMMEDIATE_BUILD_PLAN.md`, `FEATURE_PRIORITIZATION.md`, `ROADMAP.md`. Approved execution plan lives in the session plan file.

---

## ▶ RESUME HERE

- **Current work item:** `W2 — Cache invalidation (F2)` ✅ built & locally verified — **awaiting commit approval**. Next: `W3 — Citations`.
- **Branch:** `feat/cache-invalidation` (next: `feat/citations`)
- **Next action:** commit W2 (no attribution), then start W3. ⚠️ live e2e needs dev DB recreate (`docker compose down -v`) for the new columns; tests/CI don't.
- **Last completed:** W0 `fb4c639`; W1 `4b5d671`. W2 built: ruff clean, `pytest` 15 passed (+5 new), compile OK.
- **Last updated:** 2026-06-24

---

## Status legend
⬜ Not started · 🟡 In progress · ✅ Done · ⛔ Blocked

## Conventions
- Each work item gets its own branch (see table). **Commit only after user approval.**
- After each item: tick its checklist, update the ▶ RESUME pointer, add a Session Log entry, update the Metrics Ledger.
- Schema changes (W2) need a dev DB recreate (`docker compose down -v`) until Alembic lands (Phase 2).
- DoD must be met (tests pass + CI green) before an item is ✅.

---

## Master status table

| ID | Feature | Phase | Status | DoD met? | Branch | Spec |
|----|---------|-------|--------|----------|--------|------|
| W0 | Repo cleanup & credibility | 1 | ✅ | yes | `chore/cleanup-credibility` (committed `fb4c639`) | this file §W0 |
| W1 | CI + lint/type (F4) | 1 | ✅ | yes (local; live CI pending push) | `ci/github-actions` (committed `4b5d671`) | IMMEDIATE_BUILD_PLAN / FEATURE_PRIORITIZATION F4 |
| W2 | Cache invalidation + content-hash (F2) | 1 | 🟡 | local✓ / commit pending | `feat/cache-invalidation` | IMMEDIATE_BUILD_PLAN Feature 1 |
| W3 | Citations / provenance (F3) | 1 | ⬜ | no | `feat/citations` | IMMEDIATE_BUILD_PLAN Feature 2 |
| W4 | Token + USD cost tracking (F7) | 1 | ⬜ | no | `feat/cost-tracking` | FEATURE_PRIORITIZATION F7 |
| W5 | Faithfulness eval harness (F1) | 1 | ⬜ | no | `feat/faithfulness-eval` | IMMEDIATE_BUILD_PLAN Feature 3 |

---

## Phase 1 — work item checklists

### W0 — Repo cleanup & credibility ✅ (committed `fb4c639`)
- [x] Create branch `chore/cleanup-credibility`
- [x] Create `docs/BUILD_TRACKER.md`
- [x] `git rm -r --cached .venv311` (4303 → 126 tracked files; files stay on disk)
- [x] Add `.venv*/`, `venv/`, `.pycache/`, `.pytest_cache/` to `.gitignore`
- [x] Reconcile README "Benchmark Results" block to committed JSON (cold p95 10377.144 ms · semantic p95 358.951 ms · 28.91x · 18.852% · 22.549% · 0% errors); remove 69.7x
- [x] Reconcile README "Resume-Ready Summary" (28.9x)
- [x] Final review + user approval → committed `fb4c639` (authored solely by samarthshete; no co-author trailer)
- **DoD:** no venv tracked · README numbers == committed JSON · tracker live. ✅ met

### W1 — CI + lint/type safety net (F4) ✅ (committed `4b5d671`)
- [x] `pyproject.toml` (ruff E/F/I + permissive mypy; bench per-file-ignores)
- [x] `requirements-dev.txt` (ruff, mypy, pytest, httpx)
- [x] `.github/workflows/ci.yml` (lint · type[advisory] · test `MOCK_LLM=true` · docker build ×2)
- [x] README CI badge
- [x] Lint cleaned: ruff auto-fixed 34 (unused imports/import-order) + 4 manual app fixes; `ruff check` CLEAN
- [x] Tests pass locally: `pytest tests -q` → 10 passed; `compileall` OK both services
- [ ] Green CI confirmed on push/PR (needs push to GitHub)
- **DoD:** ruff + pytest + image builds pass; mypy advisory. Locally verified; live CI pending push.
- **Note:** mypy is advisory (`continue-on-error`) for now — 8 known type findings (pydantic-settings call-arg + redis sync/async typing); tighten later.

### W2 — Cache invalidation + content-hash (F2) 🟡 (built, commit pending)
- [x] `content_hash` on `Document` (models + init SQL); compute `sha256(content)` in `documents.py`
- [x] Invalidate `semantic_cache` rows on changed re-ingest (`invalidate_semantic_cache`)
- [x] `doc_content_hash` on `SemanticCacheEntry`; `store_semantic` writes it; threaded via `query.py`
- [x] `lookup_semantic` hash-check → stale entry skipped + deleted; `docusynth_semantic_cache_stale_total{event}` metric
- [x] `tests/test_semantic_cache_invalidation.py` passes (5 tests); full suite 15 passed, ruff clean
- **DoD:** regression test proves stale answer never served after changed re-ingest. ✅ met (unit-level).
- **Note:** init SQL uses `ADD COLUMN IF NOT EXISTS` for idempotency; existing dev DBs need `docker compose down -v` (no Alembic yet — Phase 2 F10).

### W3 — Citations / source provenance (F3) ⬜
- [ ] `score` on `Chunk`; `pgvector_store.retrieve` returns `1 - cosine_distance`
- [ ] `retrieve` router returns score
- [ ] `query.py` builds `citations[]` in response (+ cached payloads)
- [ ] Streamlit "📎 Sources" expander
- [ ] `docusynth_citations_per_answer` metric; tests updated
- **DoD:** every fresh answer returns citations w/ pages; UI shows them.

### W4 — Token + USD cost tracking (F7) ⬜
- [ ] `chat_completion` returns token usage (OpenAI/Gemini/Ollama shapes)
- [ ] Per-model USD price table (`config.py`); Ollama = $0
- [ ] `instrumentation.py` accumulates tokens; threaded through council
- [ ] Metrics: `docusynth_llm_tokens_total`, `docusynth_query_cost_usd`, `docusynth_cost_saved_usd_total`
- [ ] `query.py` response adds `tokens`, `cost_usd`; tests
- **DoD:** response + Prometheus show tokens/cost; cost-saved accrues on hits.

### W5 — Faithfulness eval harness (F1) ⬜
- [ ] Force-cold hook in `query.py` (bypass both caches)
- [ ] `tests/eval/faithfulness.py` (deterministic token-F1 + optional LLM-judge; groundedness)
- [ ] Threshold sweep `[0.80,0.85,0.90,0.95]` → JSON report in `docs/benchmarks/`
- [ ] Update README + `METRICS_AND_OUTCOMES.md` §7a with measured number
- [ ] Scorer determinism unit test
- **DoD:** committed faithfulness report; README cites measured retention; threshold justified by data.

---

## Phases 2–4 — backlog (⬜, detail when reached)
- **Phase 2:** F8 ownership/AuthZ + secure RAG + pin CORS · F6 OpenTelemetry tracing · F10 Alembic · F5 HNSW + hybrid + rerank · scrape RAG `/metrics` + dashboards · F14 rate-limit rewrite · F12 Terraform + verified deploy.
- **Phase 3:** F11 async ingest queue + object store · cache revalidate-on-drift · hybrid retrieval tuning (nDCG) · F13 LangGraph council (only if council kept).
- **Phase 4:** EKS/Helm/HPA · Lambda (event-driven ingest/eval) · alerting + SLOs. (Skip SageMaker/DynamoDB/Kafka.)

---

## Metrics Ledger (measured vs to-measure)
| Metric | Status | Source |
|---|---|---|
| p95 semantic-cache speedup = 28.91x | ✅ measured | `docs/benchmarks/benchmark_ollama_fast_final.json` |
| LLM-call reduction = 18.852% | ✅ measured | same |
| semantic hit rate = 22.549% | ✅ measured | same |
| error rate = 0.0% (122 queries) | ✅ measured | same |
| semantic-cache stale skips/invalidations | ✅ emitted (W2) | `docusynth_semantic_cache_stale_total{event}` |
| cache faithfulness retention | ⬜ Not measured yet | W5 |
| retrieval recall@k / nDCG | ⬜ Not measured yet | Phase 2 (F5) |
| tokens & USD cost per query / saved | ⬜ Not measured yet | W4 |
| test coverage % | ⬜ Not measured yet | W1 (add later) |

---

## Session Log
- **2026-06-24** — W0 started. Untracked `.venv311` (4303→126 tracked files). Fixed `.gitignore` venv patterns. Reconciled README benchmark block + resume summary to committed JSON (removed 69.7x → 28.91x). Created this tracker. Committed `fb4c639` (no co-author).
- **2026-06-24** — W1 built on `ci/github-actions`: added `pyproject.toml`, `requirements-dev.txt`, `.github/workflows/ci.yml`, README CI badge. ruff cleaned (34 auto-fixes + 4 manual; CLEAN). `pytest tests -q` → 10 passed; compileall OK. mypy advisory. Committed `4b5d671`. **Reminder:** all commits authored solely by samarthshete — no Claude/Anthropic attribution anywhere.
- **2026-06-24** — W2 built on `feat/cache-invalidation`: `content_hash`/`doc_content_hash` columns + init-SQL `ADD COLUMN IF NOT EXISTS`; `invalidate_semantic_cache`; hash-gated `lookup_semantic` (stale → skip+delete); `documents.py` invalidates on changed re-ingest; `query.py` threads the hash; new `docusynth_semantic_cache_stale_total{event}` metric; `tests/test_semantic_cache_invalidation.py` (5 tests). ruff clean, 15 passed. **Awaiting commit approval**, then W3 (citations).
