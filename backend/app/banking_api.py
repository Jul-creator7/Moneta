from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from . import banking_service
from .api import current_user, get_db
from .banking_schemas import Dashboard, History, Operation
from .models import User

router = APIRouter(prefix="/banking", tags=["banking"])
CurrentUser = Annotated[User, Depends(current_user)]
Database = Annotated[Session, Depends(get_db)]


@router.get("/dashboard", response_model=Dashboard)
def dashboard(user: CurrentUser, db: Database):
    return banking_service.dashboard(db, user.id)


@router.get("/transactions", response_model=History)
def history(
    user: CurrentUser, db: Database, offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
):
    return banking_service.history(db, user.id, offset, limit)


@router.post("/operations", status_code=204)
def record(operation: Operation, user: CurrentUser, db: Database):
    try:
        banking_service.record(db, user.id, operation)
    except banking_service.BankingConflict as error:
        raise HTTPException(409, str(error)) from error


@router.post("/demo", status_code=204)
def load_demo(user: CurrentUser, db: Database):
    try:
        banking_service.load_demo(db, user.id)
    except banking_service.BankingConflict as error:
        raise HTTPException(409, str(error)) from error


@router.post("/reset", status_code=204)
def reset(user: CurrentUser, db: Database):
    banking_service.reset(db, user.id)
