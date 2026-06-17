from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Plan, User, Workout
from ..schemas import PlanAdjustRequest, PlanOut, WorkoutOut, WorkoutStatusUpdate
from ..services import coach
from ..services.metrics import build_context

router = APIRouter(prefix="/plan", tags=["plan"])


@router.get("/latest", response_model=PlanOut | None)
def latest_plan(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(Plan)
        .filter(Plan.user_id == user.id)
        .order_by(Plan.created_at.desc())
        .first()
    )


@router.post("/generate", response_model=PlanOut)
def generate(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return coach.generate_plan(db, user.id)
    except coach.CoachError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/adjust", response_model=PlanOut)
def adjust(
    body: PlanAdjustRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return coach.adjust_plan(db, user.id, body.instruction)
    except coach.CoachError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/feedback")
def feedback(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Tough-but-fair coach verdict on recent training, with supporting stats."""
    return coach.weekly_feedback(db, user.id)


@router.get("/context")
def context(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """The featurized athlete context the coach reasons over (useful for debugging)."""
    return build_context(db, user.id)


@router.patch("/workout/{workout_id}", response_model=WorkoutOut)
def update_workout_status(
    workout_id: int,
    body: WorkoutStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    workout = (
        db.query(Workout)
        .filter(Workout.id == workout_id, Workout.user_id == user.id)
        .first()
    )
    if workout is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    workout.status = body.status
    db.commit()
    db.refresh(workout)
    return workout
