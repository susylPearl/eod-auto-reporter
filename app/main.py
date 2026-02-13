"""
FastAPI application entry-point.

Provides:
  - ``GET  /health``       — liveness check
  - ``POST /trigger-eod``  — manually fire the EOD pipeline

On startup the APScheduler cron job is registered; on shutdown it is
stopped cleanly.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

from app.logger import get_logger
from app.scheduler import run_eod_pipeline, start_scheduler, stop_scheduler

logger = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Lifespan (replaces deprecated startup/shutdown events)
# --------------------------------------------------------------------------- #

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Start scheduler on boot, stop on shutdown."""
    logger.info("Application starting up…")
    start_scheduler()
    yield
    logger.info("Application shutting down…")
    stop_scheduler()


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #

app = FastAPI(
    title="EOD Auto Reporter",
    description="Automated end-of-day summary from GitHub + ClickUp → Slack",
    version="1.0.0",
    lifespan=lifespan,
)


# --------------------------------------------------------------------------- #
# Response models
# --------------------------------------------------------------------------- #

class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: str
    version: str = "1.0.0"


class TriggerResponse(BaseModel):
    status: str
    message: str


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@app.get("/health", response_model=HealthResponse, tags=["ops"])
async def health_check() -> HealthResponse:
    """Liveness / readiness probe."""
    return HealthResponse(
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/trigger-eod", response_model=TriggerResponse, tags=["ops"])
async def trigger_eod(background_tasks: BackgroundTasks) -> TriggerResponse:
    """
    Manually trigger the EOD pipeline.

    The pipeline runs in a background task so the HTTP response returns
    immediately.
    """
    logger.info("Manual EOD trigger received")
    background_tasks.add_task(run_eod_pipeline)
    return TriggerResponse(
        status="accepted",
        message="EOD pipeline has been triggered and is running in the background.",
    )
