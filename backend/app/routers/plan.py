from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_auth
from ..database import get_db
from ..models import Plan, Workout
from ..schemas import PlanOut, WorkoutOut, WorkoutStatusUpdate
from ..services import coach
from ..services.metrics import build_context

router = APIRouter(prefix="/plan", tags=["plan"], dependencies=[Depends(require_auth)])


@router.get("/latest", response_model=PlanOut | None)
def latest_plan(db: Session = Depends(get_db)):
    return db.query(Plan).order_by(Plan.created_at.desc()).first()


@router.post("/generate", response_model=PlanOut)
def generate(db: Session = Depends(get_db)):
    try:
        return coach.generate_plan(db)
    except coach.CoachError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/context")
def context(db: Session = Depends(get_db)):
    """The featurized athlete context the coach reasons over (useful for debugging)."""
    return build_context(db)


@router.patch("/workout/{workout_id}", response_model=WorkoutOut)
def update_workout_status(workout_id: int, body: WorkoutStatusUpdate, db: Session = Depends(get_db)):
    workout = db.get(Workout, workout_id)
    if workout is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    workout.status = body.status
    db.commit()
    db.refresh(workout)
    return workout
