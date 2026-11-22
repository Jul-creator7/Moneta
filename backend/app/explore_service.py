from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .banking_service import lock_user
from .explore_schemas import BanknoteIdentity, BanknoteStory, EventRequest
from .models import Banknote, BanknoteEvent, Deal


class NoteNotFound(Exception):
    pass


class EventConflict(Exception):
    pass


def find_note(db: Session, identity: BanknoteIdentity) -> Banknote | None:
    return db.scalar(select(Banknote).filter_by(**identity.model_dump()))


def require_note(db: Session, identity: BanknoteIdentity) -> Banknote:
    note = find_note(db, identity)
    if note is None:
        raise NoteNotFound
    return note


def story(db: Session, note: Banknote, identity: BanknoteIdentity, before_id: int | None = None) -> BanknoteStory:
    limit = 15
    query = select(BanknoteEvent).where(BanknoteEvent.banknote_id == note.id)
    if before_id is not None:
        query = query.where(BanknoteEvent.id < before_id)
    events = db.scalars(query.order_by(BanknoteEvent.id.desc()).limit(limit + 1)).all()
    return BanknoteStory(
        note=identity, events=events[:limit], before_id=events[limit - 1].id if len(events) > limit else None,
    )


def register(db: Session, user_id: int, identity: BanknoteIdentity) -> BanknoteStory:
    lock_user(db, user_id)
    note = find_note(db, identity)
    if note is None:
        try:
            with db.begin_nested():
                note = Banknote(**identity.model_dump())
                db.add(note)
                db.flush()
        except IntegrityError:
            # A different member may have registered the same note in parallel.
            note = find_note(db, identity)
            if note is None:
                raise
    result = story(db, note, identity)
    db.commit()
    return result


def add_event(db: Session, user_id: int, data: EventRequest) -> BanknoteEvent:
    lock_user(db, user_id)
    note = require_note(db, data.note)
    fields = data.event.model_dump(exclude={"request_id"})
    request_id = str(data.event.request_id)
    event = db.scalar(select(BanknoteEvent).filter_by(user_id=user_id, request_id=request_id))
    if event is None:
        event = BanknoteEvent(banknote_id=note.id, user_id=user_id, request_id=request_id, **fields)
        db.add(event)
    elif event.banknote_id != note.id or any(getattr(event, key) != value for key, value in fields.items()):
        raise EventConflict("This request ID was already used for another story.")
    db.commit()
    db.refresh(event)
    return event


def deals(db: Session) -> list[Deal]:
    today = datetime.now(timezone.utc).date()
    return list(db.scalars(select(Deal).where(
        or_(Deal.expires_on.is_(None), Deal.expires_on >= today),
    ).order_by(Deal.city, Deal.store, Deal.id)))
