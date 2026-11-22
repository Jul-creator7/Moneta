from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from . import audit_service, goal_service, recurring_detection
from .audit_schemas import AuditedPurchase, AuditHistory, AuditInput, MoneyLeaksReport
from .banking_api import CurrentUser, Database
from .goal_schemas import Projection, ProposedPurchase

router = APIRouter(tags=["financial intelligence"])


@router.get("/audits", response_model=AuditHistory)
def history(user: CurrentUser, db: Database, before_id: Annotated[int, Query(gt=0)] | None = None):
    return audit_service.history(db, user.id, before_id)


@router.get("/audits/{transaction_id}", response_model=AuditedPurchase)
def detail(transaction_id: int, user: CurrentUser, db: Database):
    try:
        return audit_service.detail(db, user.id, transaction_id)
    except audit_service.PurchaseNotFound as error:
        raise HTTPException(404, "Purchase not found.") from error


@router.put("/audits/{transaction_id}", response_model=AuditedPurchase)
def save(transaction_id: int, data: AuditInput, user: CurrentUser, db: Database):
    try:
        return audit_service.save(db, user.id, transaction_id, data)
    except audit_service.PurchaseNotFound as error:
        raise HTTPException(404, "Purchase not found.") from error


@router.get("/audits/{transaction_id}/projection/{goal_id}", response_model=Projection)
def projection(transaction_id: int, goal_id: int, user: CurrentUser, db: Database):
    try:
        purchase = audit_service.owned_purchase(db, user.id, transaction_id)
        goal = goal_service.get_goal(db, user.id, goal_id)
    except (audit_service.PurchaseNotFound, goal_service.GoalNotFound) as error:
        raise HTTPException(404, "Purchase or savings goal not found.") from error
    return goal_service.project(goal, ProposedPurchase(amount_minor=-purchase.amount_minor, funding="contributions"))


@router.get("/money-leaks", response_model=MoneyLeaksReport)
def report(user: CurrentUser, db: Database):
    return recurring_detection.report(db, user.id)
