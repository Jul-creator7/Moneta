from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Amount = Annotated[int, Field(strict=True, ge=0, le=100_000_000)]
PositiveAmount = Annotated[int, Field(strict=True, gt=0, le=100_000_000)]


class GoalPlan(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    target_minor: PositiveAmount
    monthly_minor: Amount
    target_date: date | None = None


class GoalView(GoalPlan):
    model_config = ConfigDict(from_attributes=True)

    id: int
    allocated_minor: Amount
    created_at: datetime


class GoalsView(BaseModel):
    goals: list[GoalView]
    savings_minor: int
    unallocated_minor: int


class Allocation(BaseModel):
    allocated_minor: Amount


class ProposedPurchase(BaseModel):
    amount_minor: PositiveAmount
    funding: Literal["allocated", "contributions"]


class Timeline(BaseModel):
    starting_minor: int
    periods: int | None
    estimated_date: date | None


class Projection(BaseModel):
    as_of: date
    period_days: int
    baseline: Timeline
    with_purchase: Timeline
    delay_days: int | None
