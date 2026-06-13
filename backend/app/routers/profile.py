from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import require_auth
from ..database import get_db
from ..models import Profile
from ..schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/profile", tags=["profile"], dependencies=[Depends(require_auth)])


def _get_or_create(db: Session) -> Profile:
    profile = db.get(Profile, 1)
    if profile is None:
        profile = Profile(id=1)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db)):
    return _get_or_create(db)


@router.put("", response_model=ProfileOut)
def update_profile(body: ProfileIn, db: Session = Depends(get_db)):
    profile = _get_or_create(db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return profile
