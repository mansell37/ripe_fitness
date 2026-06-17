from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Activity, Profile, User
from ..schemas import ActivityOut, SyncResult
from ..services import garmin_sync
from ..services.metrics import build_volume_stats
from ..services.readiness import compute_readiness

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("", response_model=list[ActivityOut])
def list_activities(
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(Activity)
        .filter(Activity.user_id == user.id)
        .order_by(Activity.start_time.desc())
        .limit(limit)
        .all()
    )


@router.post("/sync", response_model=SyncResult)
def sync(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    try:
        activities_added = garmin_sync.sync_activities(db, user.id, profile)
        metrics_added = garmin_sync.sync_daily_metrics(db, user.id, profile)
    except garmin_sync.GarminAuthError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return SyncResult(
        activities_added=activities_added,
        metrics_added=metrics_added,
        message=f"Synced {activities_added} new activities and {metrics_added} daily metrics.",
    )


@router.get("/stats")
def stats(weeks: int = 8, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Weekly training volume (km / hours / sessions) by sport, vs targets."""
    return build_volume_stats(db, user.id, weeks_back=weeks)


@router.get("/readiness")
def readiness(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Today's recovery readiness score from synced wellness metrics."""
    return compute_readiness(db, user.id)


@router.get("/sync-status")
def sync_status():
    """Auto-sync schedule, next run, and last run result."""
    from ..services.scheduler import status

    return status()
