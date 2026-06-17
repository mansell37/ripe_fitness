from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    """An app user. Owns their own profile, events, plans and synced data."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime)


class Profile(Base):
    """Athlete profile — one per user."""

    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    ftp_watts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Threshold run pace in seconds per km (e.g. 245 = 4:05/km).
    threshold_pace_s_per_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resting_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Training availability — simple budget rather than rigid time slots.
    weekly_sessions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weekly_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    weekly_km_target: Mapped[float | None] = mapped_column(Float, nullable=True)
    schedule_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Standing coaching preferences that bias every plan (e.g. indoor when wet).
    coaching_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Per-user Garmin connection. We store the OAuth token blob (from the
    # bootstrap script), NOT the password — lower liability, user-revocable.
    garmin_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    garmin_token_blob: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AvailabilitySlot(Base):
    """A recurring weekly window the athlete can train in."""

    __tablename__ = "availability_slot"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    weekday: Mapped[int] = mapped_column(Integer)  # 0 = Monday … 6 = Sunday
    start_time: Mapped[str] = mapped_column(String(5))  # "06:00"
    end_time: Mapped[str] = mapped_column(String(5))  # "07:00"
    sport_preference: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)


class Event(Base):
    """A target event to periodize toward."""

    __tablename__ = "event"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    event_date: Mapped[date] = mapped_column(Date)
    event_type: Mapped[str] = mapped_column(String(50))  # marathon/half/sportive/etc.
    goal: Mapped[str | None] = mapped_column(String(200), nullable=True)  # "sub-3:00"
    priority: Mapped[str] = mapped_column(String(1), default="A")  # A/B/C race
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Activity(Base):
    """A completed activity synced from Garmin."""

    __tablename__ = "activity"
    __table_args__ = (UniqueConstraint("user_id", "garmin_id", name="uq_activity_user_garmin"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    garmin_id: Mapped[str] = mapped_column(String(50), index=True)
    sport: Mapped[str] = mapped_column(String(50))
    start_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_power: Mapped[int | None] = mapped_column(Integer, nullable=True)
    training_load: Mapped[float | None] = mapped_column(Float, nullable=True)
    calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DailyMetric(Base):
    """Daily wellness/recovery metrics from Garmin."""

    __tablename__ = "daily_metric"
    __table_args__ = (UniqueConstraint("user_id", "metric_date", name="uq_metric_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    metric_date: Mapped[date] = mapped_column(Date, index=True)
    resting_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_battery_high: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_battery_low: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stress_avg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hrv: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Plan(Base):
    """A generated weekly plan (one Claude generation)."""

    __tablename__ = "plan"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    model: Mapped[str | None] = mapped_column(String(60), nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    workouts: Mapped[list["Workout"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="Workout.workout_date"
    )


class Workout(Base):
    """A single prescribed session within a plan."""

    __tablename__ = "workout"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plan.id"))
    workout_date: Mapped[date] = mapped_column(Date, index=True)
    slot_start: Mapped[str | None] = mapped_column(String(5), nullable=True)
    sport: Mapped[str] = mapped_column(String(20))  # run/bike/gym
    title: Mapped[str] = mapped_column(String(200))
    structure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    targets: Mapped[str | None] = mapped_column(String(300), nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="planned")  # planned/done/skipped

    plan: Mapped["Plan"] = relationship(back_populates="workouts")
