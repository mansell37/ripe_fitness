from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import AvailabilitySlot, User
from ..schemas import AvailabilityIn, AvailabilityOut

router = APIRouter(prefix="/availability", tags=["availability"])


@router.get("", response_model=list[AvailabilityOut])
def list_slots(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(AvailabilitySlot)
        .filter(AvailabilitySlot.user_id == user.id)
        .order_by(AvailabilitySlot.weekday, AvailabilitySlot.start_time)
        .all()
    )


@router.post("", response_model=AvailabilityOut)
def add_slot(
    body: AvailabilityIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    slot = AvailabilitySlot(user_id=user.id, **body.model_dump())
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


@router.delete("/{slot_id}", status_code=204)
def delete_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    slot = (
        db.query(AvailabilitySlot)
        .filter(AvailabilitySlot.id == slot_id, AvailabilitySlot.user_id == user.id)
        .first()
    )
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot not found")
    db.delete(slot)
    db.commit()
