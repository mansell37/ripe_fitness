from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


# --- Auth ---
class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


# --- Profile ---
class ProfileIn(BaseModel):
    ftp_watts: int | None = None
    threshold_pace_s_per_km: int | None = None
    max_hr: int | None = None
    resting_hr: int | None = None
    weight_kg: float | None = None
    weekly_sessions: int | None = None
    weekly_hours: float | None = None
    weekly_km_target: float | None = None
    schedule_notes: str | None = None
    coaching_notes: str | None = None
    garmin_email: str | None = None
    garmin_token_blob: str | None = None  # write-only; never returned
    notes: str | None = None


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ftp_watts: int | None = None
    threshold_pace_s_per_km: int | None = None
    max_hr: int | None = None
    resting_hr: int | None = None
    weight_kg: float | None = None
    weekly_sessions: int | None = None
    weekly_hours: float | None = None
    weekly_km_target: float | None = None
    schedule_notes: str | None = None
    coaching_notes: str | None = None
    garmin_email: str | None = None
    garmin_connected: bool = False  # derived: true when a token blob is stored
    notes: str | None = None
    updated_at: datetime | None = None


# --- Availability ---
class AvailabilityIn(BaseModel):
    weekday: int
    start_time: str
    end_time: str
    sport_preference: str | None = None
    note: str | None = None


class AvailabilityOut(AvailabilityIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


# --- Events ---
class EventIn(BaseModel):
    name: str
    event_date: date
    event_type: str
    goal: str | None = None
    priority: str = "A"
    notes: str | None = None


class EventOut(EventIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


# --- Activities / metrics ---
class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sport: str
    start_time: datetime
    duration_s: float | None = None
    distance_m: float | None = None
    avg_hr: int | None = None
    avg_power: int | None = None
    training_load: float | None = None


class SyncResult(BaseModel):
    activities_added: int
    metrics_added: int
    message: str


# --- Plan / workouts ---
class WorkoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    workout_date: date
    slot_start: str | None = None
    sport: str
    title: str
    structure: dict | None = None
    targets: str | None = None
    rationale: str | None = None
    status: str


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    week_start: date
    model: str | None = None
    rationale: str | None = None
    workouts: list[WorkoutOut] = []


class WorkoutStatusUpdate(BaseModel):
    status: str  # planned/done/skipped


class PlanAdjustRequest(BaseModel):
    instruction: str
