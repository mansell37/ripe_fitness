from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Profile, User
from ..schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/profile", tags=["profile"])


def _get_or_create(db: Session, user: User) -> Profile:
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _to_out(profile: Profile) -> ProfileOut:
    out = ProfileOut.model_validate(profile)
    out.garmin_connected = bool(profile.garmin_token_blob)
    return out


@router.get("", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _to_out(_get_or_create(db, user))


@router.put("", response_model=ProfileOut)
def update_profile(
    body: ProfileIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = _get_or_create(db, user)
    data = body.model_dump(exclude_unset=True)
    # Empty-string token blob means "leave as-is"; only overwrite when provided.
    if not data.get("garmin_token_blob"):
        data.pop("garmin_token_blob", None)
    for field, value in data.items():
        setattr(profile, field, value)
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return _to_out(profile)
