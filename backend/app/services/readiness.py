"""Recovery readiness scoring.

Turns the daily wellness metrics we already sync from Garmin (sleep score,
Body Battery, resting HR vs baseline, stress) into a single 0-100 readiness
score with a label and human-readable contributing factors. Used both on the
dashboard and as context for the Claude coach.
"""

from statistics import median

from sqlalchemy.orm import Session

from ..models import DailyMetric

# Relative weights of each component when all are present.
WEIGHTS = {"sleep": 0.35, "body_battery": 0.30, "resting_hr": 0.20, "stress": 0.15}


def _label(score: float) -> tuple[str, str]:
    """Return (label, recommendation) for a readiness score."""
    if score >= 70:
        return "Go hard", "Ready for quality/intensity work."
    if score >= 50:
        return "Steady", "Moderate aerobic work; hold back on hard intensity."
    return "Back off", "Prioritise easy/recovery or rest today."


def compute_readiness(db: Session, user_id: int) -> dict | None:
    """Score the most recent day with wellness data. None if no data yet."""
    metrics = (
        db.query(DailyMetric)
        .filter(DailyMetric.user_id == user_id, DailyMetric.metric_date.isnot(None))
        .order_by(DailyMetric.metric_date.desc())
        .limit(30)
        .all()
    )
    if not metrics:
        return None

    latest = metrics[0]

    # Resting-HR baseline = median of recent days (excluding missing values).
    rhr_values = [m.resting_hr for m in metrics if m.resting_hr]
    rhr_baseline = median(rhr_values) if rhr_values else None

    components: dict[str, float] = {}
    factors: list[str] = []

    # Sleep score (0-100, higher better).
    if latest.sleep_score is not None:
        components["sleep"] = max(0, min(100, latest.sleep_score))
        hrs = round((latest.sleep_seconds or 0) / 3600, 1) if latest.sleep_seconds else None
        factors.append(
            f"Sleep score {latest.sleep_score}" + (f" ({hrs}h)" if hrs else "")
        )

    # Body Battery peak (0-100, higher better).
    if latest.body_battery_high is not None:
        components["body_battery"] = max(0, min(100, latest.body_battery_high))
        factors.append(f"Body Battery peaked at {latest.body_battery_high}")

    # Resting HR vs baseline (elevated = fatigue signal).
    if latest.resting_hr is not None and rhr_baseline:
        delta = latest.resting_hr - rhr_baseline
        # Each bpm above baseline costs ~8 pts; below baseline neutral (capped 100).
        rhr_score = max(0, min(100, 100 - max(0, delta) * 8))
        components["resting_hr"] = rhr_score
        if delta >= 2:
            factors.append(f"Resting HR {latest.resting_hr} ({int(delta)} above baseline)")
        elif delta <= -2:
            factors.append(f"Resting HR {latest.resting_hr} (below baseline — good)")
        else:
            factors.append(f"Resting HR {latest.resting_hr} (at baseline)")

    # Stress average (0-100, lower better).
    if latest.stress_avg is not None:
        components["stress"] = max(0, min(100, 100 - latest.stress_avg))
        factors.append(f"Avg stress {latest.stress_avg}")

    if not components:
        return None

    # Weighted average over the components we actually have.
    total_w = sum(WEIGHTS[k] for k in components)
    score = sum(components[k] * WEIGHTS[k] for k in components) / total_w
    score = round(score)

    label, recommendation = _label(score)
    return {
        "date": latest.metric_date.isoformat(),
        "score": score,
        "label": label,
        "recommendation": recommendation,
        "components": {k: round(v) for k, v in components.items()},
        "factors": factors,
        "resting_hr_baseline": round(rhr_baseline) if rhr_baseline else None,
    }
