"""Garmin Connect sync via the unofficial `garminconnect` library.

Token bootstrap flow (handles datacenter IP blocks):
1. If GARMIN_TOKENS_B64 env var is set, restore the session from it directly
   (no login needed). Populated by running scripts/garmin_bootstrap.py locally.
2. Try loading the cached token store directory (avoids a full login on sync).
3. Fall back to a fresh credential login (works on trusted home IPs).
"""

import base64
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Activity, DailyMetric


class GarminAuthError(RuntimeError):
    pass


def _client():
    """Return a logged-in Garmin client, reusing cached tokens when possible."""
    try:
        from garminconnect import Garmin
    except ImportError as e:  # pragma: no cover
        raise GarminAuthError("garminconnect is not installed") from e

    # 1. Try restoring session from env var (Railway / cloud deployment).
    b64 = os.environ.get("GARMIN_TOKENS_B64", "").strip()
    if b64:
        try:
            token_json = base64.b64decode(b64).decode()
            client = Garmin()
            client.client.loads(token_json)
            return client
        except Exception:
            pass

    if not settings.garmin_email or not settings.garmin_password:
        raise GarminAuthError(
            "GARMIN_EMAIL / GARMIN_PASSWORD are not configured and no "
            "GARMIN_TOKENS_B64 is set. Run scripts/garmin_bootstrap.py locally."
        )

    # 2. Try loading from the local token store directory.
    token_store = settings.garmin_token_store
    if os.path.isdir(token_store) and os.listdir(token_store):
        try:
            client = Garmin()
            client.login(token_store)
            return client
        except Exception:
            pass

    # 3. Fall back to a fresh credential login, then save tokens for next time.
    try:
        client = Garmin(settings.garmin_email, settings.garmin_password)
        client.login()
        client.client.dump(token_store)
        return client
    except Exception as e:
        raise GarminAuthError(
            "Garmin login failed from this server IP. Run "
            "scripts/garmin_bootstrap.py on your local PC and add the "
            "GARMIN_TOKENS_B64 output as a Railway environment variable."
        ) from e


def _parse_activity(a: dict) -> dict:
    """Map a Garmin activity payload to our Activity columns."""
    start = a.get("startTimeLocal") or a.get("startTimeGMT")
    start_dt = None
    if start:
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        except ValueError:
            start_dt = None
    return {
        "garmin_id": str(a.get("activityId")),
        "sport": (a.get("activityType") or {}).get("typeKey", "unknown"),
        "start_time": start_dt or datetime.now(timezone.utc),
        "duration_s": a.get("duration"),
        "distance_m": a.get("distance"),
        "avg_hr": a.get("averageHR"),
        "max_hr": a.get("maxHR"),
        "avg_power": a.get("avgPower"),
        "training_load": a.get("activityTrainingLoad"),
        "calories": a.get("calories"),
        "raw": a,
    }


def sync_activities(db: Session, limit: int = 30) -> int:
    """Pull recent activities and upsert. Returns count of newly added rows."""
    client = _client()
    activities = client.get_activities(0, limit)
    added = 0
    for a in activities:
        gid = str(a.get("activityId"))
        if not gid:
            continue
        exists = db.query(Activity).filter(Activity.garmin_id == gid).first()
        if exists:
            continue
        db.add(Activity(**_parse_activity(a)))
        added += 1
    db.commit()
    return added


def sync_daily_metrics(db: Session, days: int = 14) -> int:
    """Pull recent daily wellness metrics and upsert. Returns count added."""
    client = _client()
    added = 0
    today = datetime.now(timezone.utc).date()
    for i in range(days):
        day = today - timedelta(days=i)
        iso = day.isoformat()
        if db.query(DailyMetric).filter(DailyMetric.metric_date == day).first():
            continue
        try:
            stats = client.get_stats(iso)
            sleep = client.get_sleep_data(iso) or {}
        except Exception:
            continue
        sleep_dto = sleep.get("dailySleepDTO") or {}
        db.add(
            DailyMetric(
                metric_date=day,
                resting_hr=stats.get("restingHeartRate"),
                body_battery_high=stats.get("bodyBatteryHighestValue"),
                body_battery_low=stats.get("bodyBatteryLowestValue"),
                sleep_score=(sleep_dto.get("sleepScores") or {}).get("overall", {}).get("value"),
                sleep_seconds=sleep_dto.get("sleepTimeSeconds"),
                stress_avg=stats.get("averageStressLevel"),
                raw=stats,
            )
        )
        added += 1
    db.commit()
    return added
