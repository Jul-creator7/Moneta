from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response

from . import explore_service as explore
from .banking_api import CurrentUser, Database
from .explore_schemas import BanknoteEventView, BanknoteIdentity, BanknoteStory, DealView, EventRequest

router = APIRouter(tags=["explore"])


@router.post("/banknotes/lookup", response_model=BanknoteStory)
def lookup(
    identity: BanknoteIdentity, _user: CurrentUser, db: Database, response: Response,
    before_id: Annotated[int, Query(gt=0)] | None = None,
):
    response.headers["Cache-Control"] = "no-store"
    try:
        return explore.story(db, explore.require_note(db, identity), identity, before_id)
    except explore.NoteNotFound as error:
        raise HTTPException(404, "Banknote not registered.") from error


@router.post("/banknotes/register", response_model=BanknoteStory)
def register(identity: BanknoteIdentity, user: CurrentUser, db: Database, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return explore.register(db, user.id, identity)


@router.post("/banknotes/events", response_model=BanknoteEventView, status_code=201)
def add_event(data: EventRequest, user: CurrentUser, db: Database, response: Response):
    response.headers["Cache-Control"] = "no-store"
    try:
        return explore.add_event(db, user.id, data)
    except explore.NoteNotFound as error:
        raise HTTPException(404, "Banknote not registered.") from error
    except explore.EventConflict as error:
        raise HTTPException(409, str(error)) from error


@router.get("/deals", response_model=list[DealView])
def deals(_user: CurrentUser, db: Database):
    return explore.deals(db)
