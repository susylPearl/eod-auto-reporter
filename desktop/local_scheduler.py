"""
Local Scheduler — runs the EOD pipeline on a cron schedule in a background thread.

Uses APScheduler's ``BackgroundScheduler`` (thread-based, not asyncio) so it
works alongside the customtkinter main loop without conflict.

The scheduler reports status changes via a callback so the GUI can update
indicators in real time.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Type alias for the status callback: fn(event_type, detail_dict)
StatusCallback = Callable[[str, Dict[str, Any]], None]


class LocalScheduler:
    """Manages the background cron job for EOD report generation."""

    def __init__(self, on_status: Optional[StatusCallback] = None) -> None:
        self._scheduler = BackgroundScheduler()
        self._on_status = on_status or (lambda *_: None)
        self._running = False
        self._last_run: Optional[datetime] = None
        self._last_result: Optional[str] = None
        self._lock = threading.RLock()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_run(self) -> Optional[datetime]:
        return self._last_run

    @property
    def last_result(self) -> Optional[str]:
        return self._last_result

    def start(self, hour: int, minute: int, timezone: str) -> None:
        """Start (or restart) the scheduler with the given cron settings."""
        with self._lock:
            if self._running:
                self.stop()

            trigger = CronTrigger(
                day_of_week="mon-fri",
                hour=hour,
                minute=minute,
                timezone=timezone,
            )

            self._scheduler = BackgroundScheduler()
            self._scheduler.add_job(
                self._run_pipeline,
                trigger=trigger,
                id="desktop_eod_report",
                name="Desktop EOD Report",
                replace_existing=True,
                misfire_grace_time=3600,
            )
            self._scheduler.start()
            self._running = True

            self._on_status("scheduler_started", {
                "hour": hour,
                "minute": minute,
                "timezone": timezone,
            })
            logger.info(
                "Desktop scheduler started — EOD at %02d:%02d %s (Mon-Fri)",
                hour, minute, timezone,
            )

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        with self._lock:
            if self._scheduler.running:
                self._scheduler.shutdown(wait=False)
            self._running = False
            self._on_status("scheduler_stopped", {})
            logger.info("Desktop scheduler stopped")

    def trigger_now(self) -> None:
        """Run the EOD pipeline immediately in a background thread."""
        thread = threading.Thread(target=self._run_pipeline, daemon=True)
        thread.start()

    def _run_pipeline(self) -> None:
        """Execute the EOD pipeline and update status."""
        self._on_status("pipeline_started", {})
        logger.info("EOD pipeline triggered")

        try:
            from app.scheduler import run_eod_pipeline
            result = run_eod_pipeline()
            self._last_run = datetime.now()
            self._last_result = "success"
            self._on_status("pipeline_completed", {
                "result": result,
                "timestamp": self._last_run.isoformat(),
            })
            logger.info("EOD pipeline completed successfully")

        except Exception as exc:
            self._last_run = datetime.now()
            self._last_result = "error"
            self._on_status("pipeline_error", {
                "error": str(exc),
                "timestamp": self._last_run.isoformat() if self._last_run else "",
            })
            logger.exception("EOD pipeline failed")

    def get_next_run_time(self) -> Optional[datetime]:
        """Return the next scheduled fire time, or None."""
        try:
            job = self._scheduler.get_job("desktop_eod_report")
            if job and job.next_run_time:
                return job.next_run_time
        except Exception:
            pass
        return None
