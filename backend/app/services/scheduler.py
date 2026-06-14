"""Background auto-sync scheduler.

Pulls Garmin data three times a day (08:00 / 14:00 / 20:00 in the configured
timezone) so the dashboard and coach always have fresh data without the manual
Sync button. Failures (e.g. a Garmin auth hiccup) are logged and recorded but
never crash the app.
"""

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config import settings
from ..database import SessionLocal
from . import garmin_sync

logger = logging.getLogger("ripe_fitness.scheduler")

SYNC_HOURS = "8,14,20"
SYNC_TIMES = ["08:00", "14:00", "20:00"]

_scheduler: BackgroundScheduler | None = None
_last_run: dict = {"at": None, "ok": None, "message": None}


def _sync_job() -> None:
    global _last_run
    db = SessionLocal()
    try:
        activities = garmin_sync.sync_activities(db)
        metrics = garmin_sync.sync_daily_metrics(db)
        msg = f"Synced {activities} activities, {metrics} daily metrics"
        _last_run = {"at": datetime.now(timezone.utc).isoformat(), "ok": True, "message": msg}
        logger.info("Auto-sync: %s", msg)
    except Exception as e:  # GarminAuthError or anything unexpected
        _last_run = {"at": datetime.now(timezone.utc).isoformat(), "ok": False, "message": str(e)}
        logger.warning("Auto-sync failed: %s", e)
    finally:
        db.close()


def start_scheduler() -> None:
    global _scheduler
    if not settings.auto_sync_enabled or _scheduler is not None:
        return
    try:
        tz = ZoneInfo(settings.scheduler_timezone)
    except Exception:
        logger.warning("Bad SCHEDULER_TIMEZONE '%s'; falling back to UTC", settings.scheduler_timezone)
        tz = ZoneInfo("UTC")

    _scheduler = BackgroundScheduler(timezone=tz)
    _scheduler.add_job(
        _sync_job,
        CronTrigger(hour=SYNC_HOURS, minute=0, timezone=tz),
        id="garmin_autosync",
        replace_existing=True,
        misfire_grace_time=3600,  # tolerate a late wake-up by up to an hour
    )
    _scheduler.start()
    logger.info("Auto-sync scheduler started (%s at %s)", settings.scheduler_timezone, SYNC_HOURS)


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def status() -> dict:
    next_run = None
    if _scheduler is not None:
        job = _scheduler.get_job("garmin_autosync")
        if job and job.next_run_time:
            next_run = job.next_run_time.isoformat()
    return {
        "enabled": settings.auto_sync_enabled,
        "timezone": settings.scheduler_timezone,
        "times": SYNC_TIMES,
        "next_run": next_run,
        "last_run": _last_run,
    }
