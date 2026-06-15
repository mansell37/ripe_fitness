"""The AI coach: turns athlete context into a structured weekly plan via Claude.

We force a tool call so Claude must return JSON matching our schema (warmup /
intervals / cooldown per workout) rather than free text we'd have to parse.
"""

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Plan, Profile, Workout
from .metrics import build_context, build_volume_stats
from .readiness import compute_readiness


class CoachError(RuntimeError):
    pass


WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

SYSTEM_PROMPT = """You are an expert endurance coach building a one-week training plan for a \
single athlete training across running, cycling (Zwift, power-based) and gym/strength.

Principles:
- Periodize toward the athlete's target event using the weeks-away figure.
- Produce exactly the number of sessions the athlete has budgeted (weekly_sessions). \
Do not exceed their weekly hours budget (weekly_hours). Read their schedule_notes carefully \
to understand when they realistically train.
- Balance load against recent training load and recovery signals (sleep, body battery, \
resting HR). If recovery is poor or recent load is high, back off.
- Pay close attention to current_readiness. If the readiness label is "Back off", make the \
next 1-2 days easy or rest and move hard sessions later in the week. If "Steady", keep \
intensity moderate. If "Go hard", it's fine to schedule the week's key quality session early. \
Reference the readiness state in the week_summary so the athlete understands the adjustment.
- Use the athlete's FTP for bike power targets and threshold pace for run pace targets.
- Give every workout a clear structure (warmup, main set with explicit targets, cooldown) \
and a one-line rationale tying it to the goal or recovery state.
- Spread sessions sensibly across the week; include at least one rest day.
- The athlete ticks off sessions as they go — order matters less than quality.

Return your plan by calling the `submit_plan` tool. Do not write prose outside the tool call."""


PLAN_TOOL = {
    "name": "submit_plan",
    "description": "Submit the structured weekly training plan.",
    "input_schema": {
        "type": "object",
        "properties": {
            "week_summary": {
                "type": "string",
                "description": "2-3 sentence overview of the week's focus and how it fits the athlete's goal/recovery.",
            },
            "workouts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "weekday": {
                            "type": "string",
                            "enum": WEEKDAYS,
                            "description": "Suggested day — athlete can flex this.",
                        },
                        "sport": {"type": "string", "enum": ["run", "bike", "gym", "rest"]},
                        "title": {"type": "string"},
                        "duration_mins": {
                            "type": "integer",
                            "description": "Estimated session duration in minutes.",
                        },
                        "targets": {
                            "type": "string",
                            "description": "Short headline targets, e.g. '6x3min @ FTP' or '16km @ 4:30/km'.",
                        },
                        "structure": {
                            "type": "array",
                            "description": "Ordered steps of the session.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "phase": {
                                        "type": "string",
                                        "description": "warmup / main / cooldown",
                                    },
                                    "detail": {
                                        "type": "string",
                                        "description": "What to do, with duration and target (power/pace/HR).",
                                    },
                                },
                                "required": ["phase", "detail"],
                            },
                        },
                        "rationale": {
                            "type": "string",
                            "description": "One line: why this session this week.",
                        },
                    },
                    "required": ["weekday", "sport", "title", "structure", "rationale"],
                },
            },
        },
        "required": ["week_summary", "workouts"],
    },
}


ADJUST_SYSTEM_PROMPT = SYSTEM_PROMPT + """

You are REVISING an existing weekly plan in response to the athlete's feedback \
(provided in athlete_request, with the current plan in current_plan). Honour their \
request — schedule changes, indoor vs outdoor, swapping sessions, easing off, travel \
days — while keeping them on track toward the goal. Keep the sessions that still work \
and change only what the request implies. If a request would seriously compromise the \
goal, accommodate it as best you can and note the trade-off in week_summary."""


def _training_budget(db: Session) -> dict:
    profile = db.get(Profile, 1)
    return {
        "weekly_sessions": profile.weekly_sessions if profile else None,
        "weekly_hours": profile.weekly_hours if profile else None,
        "schedule_notes": profile.schedule_notes if profile else None,
        "coaching_preferences": profile.coaching_notes if profile else None,
    }


def _call_claude(system_prompt: str, user_payload: dict, lead_in: str) -> dict:
    if not settings.anthropic_api_key:
        raise CoachError("ANTHROPIC_API_KEY is not configured")
    try:
        from anthropic import Anthropic
    except ImportError as e:  # pragma: no cover
        raise CoachError("anthropic SDK is not installed") from e

    client = Anthropic(api_key=settings.anthropic_api_key)
    try:
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=system_prompt,
            tools=[PLAN_TOOL],
            tool_choice={"type": "tool", "name": "submit_plan"},
            messages=[{"role": "user", "content": lead_in + "\n\n" + json.dumps(user_payload, indent=2)}],
        )
    except Exception as e:
        raise CoachError(f"Claude request failed: {e}") from e

    tool_use = next((b for b in resp.content if getattr(b, "type", None) == "tool_use"), None)
    if tool_use is None:
        raise CoachError("Claude did not return a structured plan")
    return tool_use.input


def _persist_plan(db: Session, plan_data: dict) -> Plan:
    today = datetime.now(timezone.utc).date()
    week_start = today - timedelta(days=today.weekday())

    plan = Plan(
        created_at=datetime.now(timezone.utc),
        week_start=week_start,
        model=settings.anthropic_model,
        rationale=plan_data.get("week_summary"),
        raw=plan_data,
    )
    for w in plan_data.get("workouts", []):
        try:
            offset = WEEKDAYS.index(w["weekday"])
        except (ValueError, KeyError):
            offset = 0
        plan.workouts.append(
            Workout(
                workout_date=week_start + timedelta(days=offset),
                slot_start=None,
                sport=w.get("sport", "rest"),
                title=w.get("title", "Session"),
                structure={"steps": w.get("structure", [])},
                targets=w.get("targets"),
                rationale=w.get("rationale"),
                status="planned",
            )
        )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def generate_plan(db: Session) -> Plan:
    user_payload = {
        "athlete_context": build_context(db),
        "training_budget": _training_budget(db),
        "current_readiness": compute_readiness(db),
    }
    plan_data = _call_claude(
        SYSTEM_PROMPT,
        user_payload,
        "Build this week's plan from the athlete data below. "
        "Today is the reference date in athlete_context.today.",
    )
    return _persist_plan(db, plan_data)


def adjust_plan(db: Session, instruction: str) -> Plan:
    """Revise the latest plan per the athlete's free-text feedback."""
    instruction = (instruction or "").strip()
    if not instruction:
        raise CoachError("No adjustment instruction provided")

    current = db.query(Plan).order_by(Plan.created_at.desc()).first()
    user_payload = {
        "athlete_context": build_context(db),
        "training_budget": _training_budget(db),
        "current_readiness": compute_readiness(db),
        "current_plan": current.raw if current else None,
        "athlete_request": instruction,
    }
    plan_data = _call_claude(
        ADJUST_SYSTEM_PROMPT,
        user_payload,
        "Revise the current_plan to honour the athlete_request below, keeping them on "
        "track. Today is the reference date in athlete_context.today.",
    )
    return _persist_plan(db, plan_data)


FEEDBACK_SYSTEM_PROMPT = """You are a candid, experienced endurance coach reviewing an \
athlete's recent training. Give tough-but-fair feedback: be honest if they're slacking, \
skipping sessions, or under their targets; call out overreaching or poor recovery; and \
give genuine credit when they've earned it. Reference the actual numbers (adherence, \
volume vs target, trend, readiness). Keep it to 2-4 punchy sentences — direct, no fluff, \
no bullet points. End with one clear focus for the days ahead."""


def _adherence(db: Session) -> dict:
    plan = db.query(Plan).order_by(Plan.created_at.desc()).first()
    if not plan:
        return {"has_plan": False}
    counts = {"planned": 0, "done": 0, "skipped": 0}
    for w in plan.workouts:
        if w.sport == "rest":
            continue
        counts[w.status] = counts.get(w.status, 0) + 1
    total = sum(counts.values())
    done_pct = round(100 * counts["done"] / total) if total else None
    return {"has_plan": True, **counts, "total": total, "done_pct": done_pct}


def weekly_feedback(db: Session) -> dict:
    """Tough-but-fair coach verdict on recent training, with the stats behind it."""
    volume = build_volume_stats(db, weeks_back=4)
    current = volume["weeks"][0] if volume["weeks"] else None
    trailing = volume["weeks"][1:]
    trailing_avg_km = (
        round(sum(w["total_km"] for w in trailing) / len(trailing), 1) if trailing else None
    )
    stats = {
        "adherence": _adherence(db),
        "this_week_km": current["total_km"] if current else 0,
        "this_week_hours": current["total_hours"] if current else 0,
        "this_week_sessions": current["sessions"] if current else 0,
        "trailing_avg_km": trailing_avg_km,
        "targets": volume["targets"],
        "readiness": compute_readiness(db),
        "recent_activities": build_context(db)["recent_activities"][:8],
    }

    if not settings.anthropic_api_key:
        return {"stats": stats, "verdict": None, "error": "ANTHROPIC_API_KEY not configured"}

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=400,
            system=FEEDBACK_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": "Assess this athlete's recent training:\n\n"
                    + json.dumps(stats, indent=2),
                }
            ],
        )
        verdict = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
    except Exception as e:
        return {"stats": stats, "verdict": None, "error": str(e)}

    return {"stats": stats, "verdict": verdict}
