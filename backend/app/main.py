import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import admin, auth, documents, health, metrics, query
from app.audit.logger import log_tagged
from app.db.models import User
from app.db.session import SessionLocal, init_db
from app.metrics.prometheus import councilai_request_count_total, councilai_request_latency_seconds

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="DocuSynth Backend", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == "demo").first() is None:
            from app.auth.security import hash_password

            db.add(User(username="demo", password_hash=hash_password("demo123")))
            db.commit()
    finally:
        db.close()


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:  # pragma: no cover
        log_tagged("[Error]", {"path": request.url.path, "error": str(exc)})
        raise
    elapsed = time.perf_counter() - start
    councilai_request_count_total.labels(request.method, request.url.path, str(response.status_code)).inc()
    councilai_request_latency_seconds.labels(request.method, request.url.path).observe(elapsed)
    log_tagged(
        "[HTTP]",
        {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_seconds": round(elapsed, 6),
        },
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    logger.exception("[Error] unhandled exception")
    return JSONResponse(status_code=500, content={"error": str(exc)})


app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(admin.router)
app.include_router(health.router)
app.include_router(metrics.router)

