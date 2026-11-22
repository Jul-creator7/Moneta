from fastapi import APIRouter, HTTPException

from . import goal_service
from .banking_api import CurrentUser, Database
from .banking_service import BankingConflict
from .goal_schemas import Allocation, GoalPlan, GoalsView, GoalView, Projection, ProposedPurchase

router = APIRouter(prefix="/goals", tags=["goals"])


def not_found() -> HTTPException:
    return HTTPException(404, "Savings goal not found.")


@router.get("", response_model=GoalsView)
def list_goals(user: CurrentUser, db: Database):
    return goal_service.list_goals(db, user.id)


@router.post("", response_model=GoalView, status_code=201)
def create(data: GoalPlan, user: CurrentUser, db: Database):
    return goal_service.create(db, user.id, data)


@router.put("/{goal_id}", response_model=GoalView)
def edit(goal_id: int, data: GoalPlan, user: CurrentUser, db: Database):
    try:
        return goal_service.edit(db, user.id, goal_id, data)
    except goal_service.GoalNotFound as error:
        raise not_found() from error
    except BankingConflict as error:
        raise HTTPException(409, str(error)) from error


@router.put("/{goal_id}/allocation", response_model=GoalView)
def allocate(goal_id: int, data: Allocation, user: CurrentUser, db: Database):
    try:
        return goal_service.allocate(db, user.id, goal_id, data.allocated_minor)
    except goal_service.GoalNotFound as error:
        raise not_found() from error
    except BankingConflict as error:
        raise HTTPException(409, str(error)) from error


@router.post("/{goal_id}/projection", response_model=Projection)
def project(goal_id: int, data: ProposedPurchase, user: CurrentUser, db: Database):
    try:
        return goal_service.project(goal_service.get_goal(db, user.id, goal_id), data)
    except goal_service.GoalNotFound as error:
        raise not_found() from error
    except BankingConflict as error:
        raise HTTPException(409, str(error)) from error
