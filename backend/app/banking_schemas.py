from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

AccountType = Literal["chequing", "savings"]
OperationType = Literal["deposit", "income", "purchase", "bill", "transfer"]
ExpenseCategory = Literal["Food", "Shopping", "Transport", "Housing", "Utilities", "Entertainment", "Other"]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]


class Operation(BaseModel):
    operation_id: UUID
    transaction_type: OperationType
    account_type: AccountType
    destination: AccountType | None = None
    amount_minor: int = Field(strict=True, gt=0, le=100_000_000)
    merchant_name: ShortText | None = None
    category: ExpenseCategory | None = None
    description: Description | None = None

    @model_validator(mode="after")
    def validate_fields(self):
        expense = self.transaction_type in ("purchase", "bill")
        if expense and (not self.merchant_name or not self.category):
            raise ValueError("Purchases and bills require a merchant and category.")
        if not expense and (self.merchant_name or self.category):
            raise ValueError("Merchant and category apply to purchases and bills.")
        if self.transaction_type == "transfer":
            if self.destination is None or self.destination == self.account_type:
                raise ValueError("Choose a different destination account.")
        elif self.destination is not None:
            raise ValueError("A destination applies to transfers.")
        return self


class AccountView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_type: AccountType
    name: str
    currency: str
    balance_minor: int


class TransactionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    amount_minor: int
    transaction_type: OperationType
    merchant_name: str | None
    category: str
    description: str
    transfer_group_id: str | None
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def use_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class CategoryTotal(BaseModel):
    category: str
    total_minor: int


class Dashboard(BaseModel):
    accounts: list[AccountView]
    total_balance_minor: int
    savings_balance_minor: int
    monthly_income_minor: int
    monthly_spending_minor: int
    monthly_savings_rate: float | None
    spending_by_category: list[CategoryTotal]
    recent_transactions: list[TransactionView]


class History(BaseModel):
    transactions: list[TransactionView]
    next_offset: int | None
