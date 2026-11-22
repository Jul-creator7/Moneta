from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .banking_schemas import TransactionView


class AuditInput(BaseModel):
    necessity_rating: int = Field(strict=True, ge=1, le=10)
    reflection: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None


class AuditView(AuditInput):
    model_config = ConfigDict(from_attributes=True)


class AuditedPurchase(BaseModel):
    purchase: TransactionView
    audit: AuditView | None
    alternatives: list[str]


class AuditHistory(BaseModel):
    items: list[AuditedPurchase]
    before_id: int | None


class RecurringCharge(BaseModel):
    merchant: str
    category: str
    cadence: Literal["Weekly", "Monthly"]
    last_charged: date
    amount_minor: int
    annual_minor: int
    active: bool
    previous_amount_minor: int | None = None
    annual_increase_minor: int = 0


class PossibleDuplicate(BaseModel):
    merchant: str
    charged_on: date
    amount_minor: int
    count: int


class MoneyLeaksReport(BaseModel):
    recurring: list[RecurringCharge]
    duplicates: list[PossibleDuplicate]
    potential_annual_savings_minor: int
    potential_annual_increase_minor: int
