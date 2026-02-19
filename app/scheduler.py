"""
Scheduler — runs the daily EOD report pipeline.

Uses APScheduler's ``AsyncIOScheduler`` (backed by the same event loop
FastAPI uses) to fire a cron job on weekdays at the configured time.
"""

from __future__ import annotations

from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.logger import get_logger
from app.models.activity_models import ClickUpActivity, DailyActivity, GitHubActivity
from app.services import (
    clickup_service,
    github_service,
    slack_service,
    summary_service,
)

logger = get_logger(__name__)

scheduler = AsyncIOScheduler()


def _load_eod_config() -> dict:
    """Load desktop config for EOD pipeline (filters, manual updates)."""
    try:
        from desktop.config_store import load_config  # type: ignore
        return load_config()
    except Exception:
        return {}


def _load_manual_updates() -> list[str]:
    """
    Best-effort load manual updates from desktop config.

    Keeps backend usage safe by falling back to [] when desktop modules
    are unavailable.
    """
    cfg = _load_eod_config()
    raw = cfg.get("manual_updates", [])
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip()][:30]


def run_eod_pipeline() -> str:
    """
    Execute the full EOD pipeline synchronously:

    1. Check if user is OOO → skip if true.
    2. Fetch GitHub activity.
    3. Fetch ClickUp activity.
    4. Generate summary.
    5. Post to Slack.

    Returns:
        The generated summary text, or a skip/error reason string.
    """
    logger.info("=== EOD Pipeline started ===")

    # --- OOO guard -----------------------------------------------------------
    if slack_service.is_user_ooo():
        msg = "Skipping EOD report — user is marked OOO in Slack."
        logger.info(msg)
        return msg

    # --- Collect activity (respect Activity tab filters) -----------------------
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cfg = _load_eod_config()
    show_github = cfg.get("show_github", True)
    show_clickup = cfg.get("show_clickup", True)
    show_manual = cfg.get("show_manual", True)
    if not (show_github and show_clickup and show_manual):
        logger.info("EOD filters: github=%s, clickup=%s, manual=%s", show_github, show_clickup, show_manual)

    gh_activity = github_service.fetch_github_activity() if show_github else GitHubActivity()
    cu_activity = clickup_service.fetch_clickup_activity() if show_clickup else ClickUpActivity()
    manual_updates = _load_manual_updates() if show_manual else []

    daily = DailyActivity(
        date=today,
        github=gh_activity,
        clickup=cu_activity,
        manual_updates=manual_updates,
    )

    # --- Generate summary -----------------------------------------------------
    blocks = summary_service.generate_summary_blocks(daily)
    fallback_text = summary_service.generate_summary(daily)

    # --- Post to Slack --------------------------------------------------------
    channel = settings.slack_channel
    success = slack_service.send_message(channel, fallback_text, blocks=blocks)

    if success:
        logger.info("=== EOD Pipeline completed — message sent to %s ===", channel)
    else:
        logger.error("=== EOD Pipeline completed — Slack send FAILED ===")

    return fallback_text


def _scheduled_eod_job() -> None:
    """Wrapper called by APScheduler's cron trigger."""
    try:
        run_eod_pipeline()
    except Exception:
        logger.exception("Unhandled error in scheduled EOD job")


def start_scheduler() -> None:
    """
    Register the daily cron job and start the scheduler.

    The job runs Monday–Friday (``day_of_week='mon-fri'``) at the hour
    and minute defined in settings.
    """
    trigger = CronTrigger(
        day_of_week="mon-fri",
        hour=settings.report_hour,
        minute=settings.report_minute,
        timezone=settings.timezone,
    )

    scheduler.add_job(
        _scheduled_eod_job,
        trigger=trigger,
        id="daily_eod_report",
        name="Daily EOD Report",
        replace_existing=True,
        misfire_grace_time=3600,  # allow up to 1 h late if the server was down
    )

    scheduler.start()
    logger.info(
        "Scheduler started — EOD report runs Mon-Fri at %02d:%02d %s",
        settings.report_hour,
        settings.report_minute,
        settings.timezone,
    )


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
