"""The AI coach: turns athlete context into a structured weekly plan via Claude.

We force a tool call so Claude must return JSON matching our schema (warmup /
intervals / cooldown per workout) rather than free text we'd have to parse.
"""

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Plan, Profile, Workout
from .metrics import build_context


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


def _training_budget(db: Session) -> dict:
    profile = db.get(Profile, 1)
    return {
        "weekly_sessions": profile.weekly_sessions if profile else None,
        "weekly_hours": profile.weekly_hours if profile else None,
        "schedule_notes": profile.schedule_notes if profile else None,
    }


def generate_plan(db: Session) -> Plan:
    if not settings.anthropic_api_key:
        raise CoachError("ANTHROPIC_API_KEY is not configured")

    try:
        from anthropic import Anthropic
    except ImportError as e:  # pragma: no cover
        raise CoachError("anthropic SDK is not installed") from e

    context = build_context(db)
    budget = _training_budget(db)

    user_payload = {
        "athlete_context": context,
        "training_budget": budget,
    }

    client = Anthropic(api_key=settings.anthropic_api_key)
    try:
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=[PLAN_TOOL],
            tool_choice={"type": "tool", "name": "submit_plan"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Build this week's plan from the athlete data below. "
                        "Today is the reference date in athlete_context.today.\n\n"
                        + json.dumps(user_payload, indent=2)
                    ),
                }
            ],
        )
    except Exception as e:
        raise CoachError(f"Claude request failed: {e}") from e

    tool_use = next((b for b in resp.content if getattr(b, "type", None) == "tool_use"), None)
    if tool_use is None:
        raise CoachError("Claude did not return a structured plan")
    plan_data = tool_use.input

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
