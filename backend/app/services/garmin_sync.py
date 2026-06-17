"""Per-user Garmin Connect sync via the unofficial `garminconnect` library.

Each user stores their own OAuth token blob on their profile (produced by the
bootstrap script). We restore the session from that blob — we never store
Garmin passwords. If a user hasn't connected Garmin, sync is a no-op error.
"""

import base64
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..models import Activity, DailyMetric, Profile


class GarminAuthError(RuntimeError):
    pass


def _client(profile: Profile | None):
    """Return a Garmin client restored from the user's stored token blob."""
    try:
        from garminconnect import Garmin
    except ImportError as e:  # pragma: no cover
        raise GarminAuthError("garminconnect is not installed") from e

    if profile is None or not profile.garmin_token_blob:
        raise GarminAuthError(
            "Garmin is not connected for this account. Add your Garmin token "
            "(from the bootstrap script) in the Goals tab."
        )
    try:
        token_json = base64.b64decode(profile.garmin_token_blob).decode()
        client = Garmin()
        client.client.loads(token_json)
        return client
    except Exception as e:
        raise GarminAuthError(
            "Stored Garmin token is invalid or expired. Re-run the bootstrap "
            "script and update your Garmin token in the Goals tab."
        ) from e


def _parse_activity(a: dict, user_id: int) -> dict:
    start = a.get("startTimeLocal") or a.get("startTimeGMT")
    start_dt = None
    if start:
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        except ValueError:
            start_dt = None
    return {
        "user_id": user_id,
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


def sync_activities(db: Session, user_id: int, profile: Profile, limit: int = 30) -> int:
    """Pull recent activities for one user and upsert. Returns new-row count."""
    client = _client(profile)
    activities = client.get_activities(0, limit)
    added = 0
    for a in activities:
        gid = str(a.get("activityId"))
        if not gid:
            continue
        exists = (
            db.query(Activity)
            .filter(Activity.user_id == user_id, Activity.garmin_id == gid)
            .first()
        )
        if exists:
            continue
        db.add(Activity(**_parse_activity(a, user_id)))
        added += 1
    db.commit()
    return added


def sync_daily_metrics(db: Session, user_id: int, profile: Profile, days: int = 14) -> int:
    """Pull recent daily wellness metrics for one user. Returns new-row count."""
    client = _client(profile)
    added = 0
    today = datetime.now(timezone.utc).date()
    for i in range(days):
        day = today - timedelta(days=i)
        iso = day.isoformat()
        exists = (
            db.query(DailyMetric)
            .filter(DailyMetric.user_id == user_id, DailyMetric.metric_date == day)
            .first()
        )
        if exists:
            continue
        try:
            stats = client.get_stats(iso)
            sleep = client.get_sleep_data(iso) or {}
        except Exception:
            continue
        sleep_dto = sleep.get("dailySleepDTO") or {}
        db.add(
            DailyMetric(
                user_id=user_id,
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
