"""Featurization layer.

Turns raw activities + daily metrics into a compact, structured summary that
gives Claude clean context to reason over (recent load, trend, freshness,
days-to-event). This is *context for the LLM*, not a separate rules engine.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..models import Activity, DailyMetric, Event, Profile


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


def build_context(db: Session) -> dict:
    """Assemble the full athlete context payload for plan generation."""
    today = datetime.now(timezone.utc).date()

    profile = db.get(Profile, 1)
    activities = (
        db.query(Activity)
        .filter(Activity.start_time >= datetime.now(timezone.utc) - timedelta(days=42))
        .order_by(Activity.start_time.desc())
        .all()
    )
    metrics = (
        db.query(DailyMetric)
        .filter(DailyMetric.metric_date >= today - timedelta(days=10))
        .order_by(DailyMetric.metric_date.desc())
        .all()
    )
    events = (
        db.query(Event)
        .filter(Event.event_date >= today)
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
