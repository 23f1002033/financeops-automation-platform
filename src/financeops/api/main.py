"""FastAPI application entry point.

Run: uvicorn financeops.api.main:app --reload --port 8000
Docs at /docs (Swagger) and /redoc.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from financeops.api.routers import anomalies, ingestion, kpis, reports
from financeops.api.schemas import HealthResponse
from financeops.config import get_settings
from financeops.db.session import init_db
from financeops.logging_config import get_logger
from financeops import __version__

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("API startup complete (%s)", settings.environment)
    yield
    logger.info("API shutdown")


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Corporate finance automation: ingestion, KPIs, anomalies, reporting.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000
    logger.info("%s %s -> %s (%.1f ms)", request.method, request.url.path, response.status_code, elapsed)
    response.headers["X-Process-Time-ms"] = f"{elapsed:.1f}"
    return response


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health():
    return HealthResponse(app=settings.app_name, version=__version__, environment=settings.environment)


app.include_router(kpis.router)
app.include_router(anomalies.router)
app.include_router(ingestion.router)
app.include_router(reports.router)