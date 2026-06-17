"""Featurization layer.

Turns raw activities + daily metrics into a compact, structured summary that
gives Claude clean context to reason over (recent load, trend, freshness,
days-to-event). This is *context for the LLM*, not a separate rules engine.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..models import Activity, DailyMetric, Event, Profile


# Map Garmin's many activityType keys into our three buckets.
def sport_bucket(garmin_sport: str) -> str:
    s = (garmin_sport or "").lower()
    if "run" in s or "treadmill" in s:
        return "run"
    if "cycl" in s or "bik" in s or "ride" in s:
        return "bike"
    if "strength" in s or "cardio" in s or "fitness_equipment" in s or "gym" in s:
        return "gym"
    return "other"


def _week_load(activities: list[Activity], start: date, end: date) -> dict:
    window = [
        a for a in activities if start <= a.start_time.date() <= end
    ]
    total_load = sum((a.training_load or 0) for a in window)
    total_minutes = sum((a.duration_s or 0) for a in window) / 60.0
    by_sport: dict[str, float] = {}
    for a in window:
        by_sport[a.sport] = by_sport.get(a.sport, 0) + (a.duration_s or 0) / 60.0
    return {
        "sessions": len(window),
        "total_load": round(total_load, 1),
        "total_minutes": round(total_minutes, 1),
        "minutes_by_sport": {k: round(v, 1) for k, v in by_sport.items()},
    }


def build_context(db: Session, user_id: int) -> dict:
    """Assemble the full athlete context payload for plan generation."""
    today = datetime.now(timezone.utc).date()

    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    activities = (
        db.query(Activity)
        .filter(
            Activity.user_id == user_id,
            Activity.start_time >= datetime.now(timezone.utc) - timedelta(days=42),
        )
        .order_by(Activity.start_time.desc())
        .all()
    )
    metrics = (
        db.query(DailyMetric)
        .filter(
            DailyMetric.user_id == user_id,
            DailyMetric.metric_date >= today - timedelta(days=10),
        )
        .order_by(DailyMetric.metric_date.desc())
        .all()
    )
    events = (
        db.query(Event)
        .filter(Event.user_id == user_id, Event.event_date >= today)
        .order_by(Event.event_date.asc())
        .all()
    )

    this_week_start = today - timedelta(days=today.weekday())
    weekly = []
    for w in range(4):
        ws = this_week_start - timedelta(weeks=w)
        weekly.append({"week_start": ws.isoformat(), **_week_load(activities, ws, ws + timedelta(days=6))})

    recent_metrics = [
        {
            "date": m.metric_date.isoformat(),
            "resting_hr": m.resting_hr,
            "body_battery_high": m.body_battery_high,
            "sleep_score": m.sleep_score,
            "sleep_hours": round((m.sleep_seconds or 0) / 3600, 1) if m.sleep_seconds else None,
            "stress_avg": m.stress_avg,
        }
        for m in metrics
    ]

    next_event = events[0] if events else None
    return {
        "today": today.isoformat(),
        "profile": {
            "ftp_watts": profile.ftp_watts if profile else None,
            "threshold_pace_s_per_km": profile.threshold_pace_s_per_km if profile else None,
            "max_hr": profile.max_hr if profile else None,
            "resting_hr": profile.resting_hr if profile else None,
            "weight_kg": profile.weight_kg if profile else None,
        },
        "next_event": (
            {
                "name": next_event.name,
                "date": next_event.event_date.isoformat(),
                "type": next_event.event_type,
                "goal": next_event.goal,
                "weeks_away": (next_event.event_date - today).days // 7,
            }
            if next_event
            else None
        ),
        "recent_activities": [
            {
                "date": a.start_time.date().isoformat(),
                "sport": a.sport,
                "minutes": round((a.duration_s or 0) / 60, 1),
                "distance_km": round((a.distance_m or 0) / 1000, 2) if a.distance_m else None,
                "avg_hr": a.avg_hr,
                "avg_power": a.avg_power,
                "training_load": a.training_load,
            }
            for a in activities[:15]
        ],
        "weekly_load": weekly,
        "recent_metrics": recent_metrics,
    }


def build_volume_stats(db: Session, user_id: int, weeks_back: int = 8) -> dict:
    """Weekly training volume (km / hours / sessions) by sport, vs targets."""
    today = datetime.now(timezone.utc).date()
    this_week_start = today - timedelta(days=today.weekday())
    earliest = this_week_start - timedelta(weeks=weeks_back - 1)

    activities = (
        db.query(Activity)
        .filter(
            Activity.user_id == user_id,
            Activity.start_time >= datetime.combine(earliest, datetime.min.time()),
        )
        .all()
    )

    weeks = []
    for w in range(weeks_back):
        ws = this_week_start - timedelta(weeks=w)
        we = ws + timedelta(days=6)
        window = [a for a in activities if ws <= a.start_time.date() <= we]

        by_sport: dict[str, dict] = {}
        for a in window:
            b = sport_bucket(a.sport)
            agg = by_sport.setdefault(b, {"km": 0.0, "hours": 0.0, "sessions": 0})
            agg["km"] += (a.distance_m or 0) / 1000
            agg["hours"] += (a.duration_s or 0) / 3600
            agg["sessions"] += 1

        weeks.append(
            {
                "week_start": ws.isoformat(),
                "is_current": ws == this_week_start,
                "total_km": round(sum(s["km"] for s in by_sport.values()), 1),
                "total_hours": round(sum(s["hours"] for s in by_sport.values()), 1),
                "sessions": len(window),
                "by_sport": {
                    k: {
                        "km": round(v["km"], 1),
                        "hours": round(v["hours"], 1),
                        "sessions": v["sessions"],
                    }
                    for k, v in by_sport.items()
                },
            }
        )

    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    return {
        "weeks": weeks,  # index 0 = current week, then trailing
        "targets": {
            "weekly_hours": profile.weekly_hours if profile else None,
            "weekly_km": profile.weekly_km_target if profile else None,
            "weekly_sessions": profile.weekly_sessions if profile else None,
        },
    }
