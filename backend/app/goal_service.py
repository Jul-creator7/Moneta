from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .banking_defaults import CURRENCY
from .banking_service import BankingConflict, lock_user
from .goal_schemas import GoalPlan, GoalsView, Projection, ProposedPurchase, Timeline
from .models import BankAccount, SavingsGoal

PERIOD_DAYS = 30


class GoalNotFound(Exception):
    pass


def list_goals(db: Session, user_id: int) -> GoalsView:
    rows = db.execute(select(BankAccount.balance_minor, SavingsGoal)
        .outerjoin(SavingsGoal, SavingsGoal.user_id == BankAccount.user_id)
        .where(BankAccount.user_id == user_id, BankAccount.account_type == "savings", BankAccount.currency == CURRENCY)
        .order_by(SavingsGoal.id)).all()
    savings = rows[0][0]
    goals = [goal for _, goal in rows if goal is not None]
    return GoalsView(
        goals=goals, savings_minor=savings,
        unallocated_minor=savings - sum(goal.allocated_minor for goal in goals),
    )


def get_goal(db: Session, user_id: int, goal_id: int) -> SavingsGoal:
    goal = db.scalar(select(SavingsGoal).where(SavingsGoal.user_id == user_id, SavingsGoal.id == goal_id))
    if goal is None:
        raise GoalNotFound
    return goal


def create(db: Session, user_id: int, data: GoalPlan) -> SavingsGoal:
    goal = SavingsGoal(user_id=user_id, **data.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def edit(db: Session, user_id: int, goal_id: int, data: GoalPlan) -> SavingsGoal:
    lock_user(db, user_id)
    goal = get_goal(db, user_id, goal_id)
    if data.target_minor < goal.allocated_minor:
        raise BankingConflict("Release some allocated savings before lowering the target.")
    goal.name = data.name
    goal.target_minor = data.target_minor
    goal.monthly_minor = data.monthly_minor
    goal.target_date = data.target_date
    db.commit()
    db.refresh(goal)
    return goal


def allocate(db: Session, user_id: int, goal_id: int, amount: int) -> SavingsGoal:
    lock_user(db, user_id)
    goal = get_goal(db, user_id, goal_id)
    if amount > goal.target_minor:
        raise BankingConflict("The allocation cannot exceed the goal target.")
    available = list_goals(db, user_id).unallocated_minor + goal.allocated_minor
    if amount > available:
        raise BankingConflict("There is not enough unallocated money in savings.")
    goal.allocated_minor = amount
    db.commit()
    db.refresh(goal)
    return goal


def timeline(today: date, start: int, target: int, monthly: int, diverted: int = 0) -> Timeline:
    remaining = target - start
    if remaining <= 0:
        return Timeline(starting_minor=start, periods=0, estimated_date=today)
    if monthly == 0:
        return Timeline(starting_minor=start, periods=None, estimated_date=None)
    periods = (remaining + diverted + monthly - 1) // monthly
    days = periods * PERIOD_DAYS
    estimated_date = today + timedelta(days=days) if days <= (date.max - today).days else None
    return Timeline(starting_minor=start, periods=periods, estimated_date=estimated_date)


def project(goal: SavingsGoal, purchase: ProposedPurchase) -> Projection:
    start = goal.allocated_minor
    diverted = 0
    if purchase.funding == "allocated":
        if purchase.amount_minor > start:
            raise BankingConflict("The purchase exceeds this goal's allocated savings.")
        start -= purchase.amount_minor
    else:
        diverted = purchase.amount_minor

    today = datetime.now(timezone.utc).date()
    baseline = timeline(today, goal.allocated_minor, goal.target_minor, goal.monthly_minor)
    alternative = timeline(today, start, goal.target_minor, goal.monthly_minor, diverted)
    delay = None
    if baseline.periods is not None and alternative.periods is not None:
        delay = (alternative.periods - baseline.periods) * PERIOD_DAYS
    return Projection(as_of=today, period_days=PERIOD_DAYS, baseline=baseline, with_purchase=alternative, delay_days=delay)
