This directory is archived and not part of the active runtime stack.

- The active control plane now lives in `backend/` (Python 3.11 + FastAPI).
- `docker-compose.yml` no longer starts this service.
- The native semantic cache implementation under `internal/cache/fastcache/` is also archived.

Kept temporarily for migration traceability.
