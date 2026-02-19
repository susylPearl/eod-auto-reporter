"""
FastAPI application entry-point.

Provides:
  - ``GET  /health``           — liveness check
  - ``POST /trigger-eod``      — manually fire the EOD pipeline
  - ``GET  /api/activity``     — today's aggregated activity
  - ``GET  /api/stats``        — quick stat counts
  - ``GET  /api/scheduler``    — scheduler status

On startup the APScheduler cron job is registered; on shutdown it is
stopped cleanly.
"""

from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.logger import get_logger
from app.scheduler import run_eod_pipeline, scheduler, start_scheduler, stop_scheduler

logger = get_logger(__name__)

_last_pipeline_result: Dict[str, Any] = {"timestamp": None, "status": None, "error": None}
_send_lock = threading.Lock()


# --------------------------------------------------------------------------- #
# Lifespan
# --------------------------------------------------------------------------- #

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


class StatsResponse(BaseModel):
    commits: int = 0
    prs: int = 0
    completed: int = 0
    in_progress: int = 0


class SchedulerStatusResponse(BaseModel):
    running: bool
    next_run: Optional[str] = None
    last_run: Optional[str] = None
    last_status: Optional[str] = None
    schedule_time: str = ""
    timezone: str = ""


# --------------------------------------------------------------------------- #
# Endpoints — ops
# --------------------------------------------------------------------------- #

@app.get("/health", response_model=HealthResponse, tags=["ops"])
async def health_check() -> HealthResponse:
    return HealthResponse(timestamp=datetime.now(timezone.utc).isoformat())


@app.post("/trigger-eod", response_model=TriggerResponse, tags=["ops"])
async def trigger_eod(background_tasks: BackgroundTasks) -> TriggerResponse:
    logger.info("Manual EOD trigger received")

    def _run():
        with _send_lock:
            try:
                run_eod_pipeline()
                _last_pipeline_result.update(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status="success", error=None,
                )
            except Exception as exc:
                _last_pipeline_result.update(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status="error", error=str(exc)[:200],
                )

    background_tasks.add_task(_run)
    return TriggerResponse(
        status="accepted",
        message="EOD pipeline has been triggered and is running in the background.",
    )


# --------------------------------------------------------------------------- #
# Endpoints — mobile API
# --------------------------------------------------------------------------- #

@app.get("/api/activity", tags=["mobile"])
async def get_activity():
    """Return today's raw activity from all sources."""
    from app.services import clickup_service, github_service

    gh = None
    cu = None
    errors: List[str] = []

    try:
        gh = github_service.fetch_github_activity()
    except Exception as exc:
        errors.append(f"GitHub: {str(exc)[:100]}")

    try:
        cu = clickup_service.fetch_clickup_activity()
    except Exception as exc:
        errors.append(f"ClickUp: {str(exc)[:100]}")

    return {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "github": gh.model_dump() if gh else None,
        "clickup": cu.model_dump() if cu else None,
        "errors": errors,
    }


@app.get("/api/stats", response_model=StatsResponse, tags=["mobile"])
async def get_stats():
    """Quick stat counts for the dashboard."""
    from app.services import clickup_service, github_service

    commits = prs = completed = in_progress = 0
    try:
        gh = github_service.fetch_github_activity()
        commits = len(gh.commits)
        prs = len(gh.prs_opened) + len(gh.prs_merged)
    except Exception:
        pass
    try:
        cu = clickup_service.fetch_clickup_activity()
        completed = len(cu.tasks_completed)
        in_progress = len(cu.status_changes)
    except Exception:
        pass

    return StatsResponse(
        commits=commits, prs=prs, completed=completed, in_progress=in_progress,
    )


@app.get("/api/scheduler", response_model=SchedulerStatusResponse, tags=["mobile"])
async def get_scheduler_status():
    """Current scheduler state."""
    from app.config import settings

    running = scheduler.running if scheduler else False
    next_run = None
    if running:
        jobs = scheduler.get_jobs()
        if jobs:
            nrt = jobs[0].next_run_time
            next_run = nrt.isoformat() if nrt else None

    return SchedulerStatusResponse(
        running=running,
        next_run=next_run,
        last_run=_last_pipeline_result.get("timestamp"),
        last_status=_last_pipeline_result.get("status"),
        schedule_time=f"{settings.report_hour:02d}:{settings.report_minute:02d}",
        timezone=settings.timezone,
    )
