from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Event, User
from ..schemas import EventIn, EventOut

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventOut])
def list_events(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(Event)
        .filter(Event.user_id == user.id)
        .order_by(Event.event_date)
        .all()
    )


@router.post("", response_model=EventOut)
def add_event(
    body: EventIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = Event(user_id=user.id, **body.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=204)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = db.query(Event).filter(Event.id == event_id, Event.user_id == user.id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(event)
    db.commit()
