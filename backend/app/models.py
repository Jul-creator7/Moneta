from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BankAccount(Base):
    __tablename__ = "bank_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "account_type", "currency", name="uq_bank_account_owner_type_currency"),
        CheckConstraint("balance_minor >= 0", name="ck_bank_account_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    account_type: Mapped[str] = mapped_column(String(24))
    name: Mapped[str] = mapped_column(String(80))
    currency: Mapped[str] = mapped_column(String(3))
    balance_minor: Mapped[int] = mapped_column(BigInteger, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("account_id", "operation_id", name="uq_transaction_account_operation"),
        CheckConstraint("amount_minor != 0", name="ck_transaction_nonzero"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("bank_accounts.id"))
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    transaction_type: Mapped[str] = mapped_column(String(24))
    merchant_name: Mapped[str | None] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(String(160))
    operation_id: Mapped[str] = mapped_column(String(36))
    transfer_group_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
