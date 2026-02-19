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

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MISSED,
    JobExecutionEvent,
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Route APScheduler's own logs so errors don't vanish silently.
_aps_logger = logging.getLogger("apscheduler")
if not _aps_logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
    _aps_logger.addHandler(_h)
    _aps_logger.setLevel(logging.INFO)

StatusCallback = Callable[[str, Dict[str, Any]], None]


class LocalScheduler:
    """Manages the background cron job for EOD report generation."""

    def __init__(self, on_status: Optional[StatusCallback] = None) -> None:
        self._scheduler: Optional[BackgroundScheduler] = None
        self._on_status = on_status or (lambda *_: None)
        self._running = False
        self._last_run: Optional[datetime] = None
        self._last_result: Optional[str] = None
        self._lock = threading.RLock()
        # Stored so check_health() can restart with the same settings.
        self._hour = 18
        self._minute = 0
        self._timezone = "Asia/Kathmandu"

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

            self._hour = hour
            self._minute = minute
            self._timezone = timezone

            trigger = CronTrigger(
                day_of_week="mon-fri",
                hour=hour,
                minute=minute,
                timezone=timezone,
            )

            self._scheduler = BackgroundScheduler(daemon=True)
            self._scheduler.add_listener(
                self._on_job_event,
                EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED,
            )
            self._scheduler.add_job(
                self._run_pipeline,
                trigger=trigger,
                id="desktop_eod_report",
                name="Desktop EOD Report",
                replace_existing=True,
                misfire_grace_time=14400,  # 4 hours — survives long macOS sleep
                coalesce=True,
                max_instances=1,
            )
            self._scheduler.start()
            self._running = True

            nrt = self.get_next_run_time()
            self._on_status("scheduler_started", {
                "hour": hour,
                "minute": minute,
                "timezone": timezone,
                "next_run": nrt.isoformat() if nrt else None,
            })
            logger.info(
                "Desktop scheduler started — EOD at %02d:%02d %s (Mon-Fri), next: %s",
                hour, minute, timezone,
                nrt.strftime("%Y-%m-%d %H:%M %Z") if nrt else "N/A",
            )

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        with self._lock:
            if self._scheduler and self._scheduler.running:
                self._scheduler.shutdown(wait=False)
            self._running = False
            self._scheduler = None
            self._on_status("scheduler_stopped", {})
            logger.info("Desktop scheduler stopped")

    def trigger_now(self) -> None:
        """Run the EOD pipeline immediately in a background thread."""
        thread = threading.Thread(target=self._run_pipeline, daemon=True)
        thread.start()

    def check_health(self) -> bool:
        """
        Verify the scheduler thread is still alive.

        If it died (e.g. unhandled error in APScheduler's main loop,
        or macOS froze the thread), restart automatically.

        Returns True if healthy, False if a restart was needed.
        """
        with self._lock:
            if not self._running:
                return True

            if self._scheduler is None or not self._scheduler.running:
                logger.warning("Scheduler thread died — restarting automatically")
                self._running = False
                self.start(self._hour, self._minute, self._timezone)
                return False

        return True

    # ------------------------------------------------------------------ #
    # APScheduler event listener
    # ------------------------------------------------------------------ #

    def _on_job_event(self, event: JobExecutionEvent) -> None:
        if event.code == EVENT_JOB_EXECUTED:
            logger.info("Scheduled job executed successfully")
        elif event.code == EVENT_JOB_ERROR:
            logger.error("Scheduled job raised an exception: %s", event.exception)
        elif event.code == EVENT_JOB_MISSED:
            logger.warning(
                "Scheduled job missed (fire time: %s) — system was likely asleep",
                event.scheduled_run_time,
            )
            self._on_status("job_missed", {
                "scheduled_time": str(event.scheduled_run_time),
            })

    # ------------------------------------------------------------------ #
    # Pipeline
    # ------------------------------------------------------------------ #

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
            if self._scheduler:
                job = self._scheduler.get_job("desktop_eod_report")
                if job and job.next_run_time:
                    return job.next_run_time
        except Exception:
            pass
        return None
