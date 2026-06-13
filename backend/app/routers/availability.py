from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_auth
from ..database import get_db
from ..models import AvailabilitySlot
from ..schemas import AvailabilityIn, AvailabilityOut

router = APIRouter(prefix="/availability", tags=["availability"], dependencies=[Depends(require_auth)])


@router.get("", response_model=list[AvailabilityOut])
def list_slots(db: Session = Depends(get_db)):
    return (
        db.query(AvailabilitySlot)
        .order_by(AvailabilitySlot.weekday, AvailabilitySlot.start_time)
        .all()
    )


@router.post("", response_model=AvailabilityOut)
def add_slot(body: AvailabilityIn, db: Session = Depends(get_db)):
    slot = AvailabilitySlot(**body.model_dump())
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


@router.delete("/{slot_id}", status_code=204)
def delete_slot(slot_id: int, db: Session = Depends(get_db)):
    slot = db.get(AvailabilitySlot, slot_id)
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot not found")
    db.delete(slot)
    db.commit()
