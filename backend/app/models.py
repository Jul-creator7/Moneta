from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Float, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(80))
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


class SavingsGoal(Base):
    __tablename__ = "savings_goals"
    __table_args__ = (
        CheckConstraint("target_minor > 0", name="ck_goal_positive_target"),
        CheckConstraint("allocated_minor >= 0 AND allocated_minor <= target_minor", name="ck_goal_allocation"),
        CheckConstraint("monthly_minor >= 0", name="ck_goal_monthly_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    target_minor: Mapped[int] = mapped_column(BigInteger)
    allocated_minor: Mapped[int] = mapped_column(BigInteger, server_default="0")
    monthly_minor: Mapped[int] = mapped_column(BigInteger)
    target_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TransactionAudit(Base):
    __tablename__ = "transaction_audits"
    __table_args__ = (
        CheckConstraint("necessity_rating BETWEEN 1 AND 10", name="ck_audit_rating_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), unique=True,
    )
    necessity_rating: Mapped[int]
    reflection: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint("author_id", "request_id", name="uq_post_author_request"),
        CheckConstraint("post_type IN ('discussion', 'achievement')", name="ck_post_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    image: Mapped[str | None] = mapped_column(Text)
    post_type: Mapped[str] = mapped_column(String(20))
    request_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PostLike(Base):
    __tablename__ = "post_likes"

    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (UniqueConstraint("user_id", "request_id", name="uq_comment_user_request"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    request_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Banknote(Base):
    __tablename__ = "banknotes"
    __table_args__ = (
        UniqueConstraint("currency", "denomination", "serial_number", "series", name="uq_banknote_identity"),
        CheckConstraint("denomination > 0", name="ck_banknote_positive_denomination"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    currency: Mapped[str] = mapped_column(String(3))
    denomination: Mapped[int]
    serial_number: Mapped[str] = mapped_column(String(32))
    series: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BanknoteEvent(Base):
    __tablename__ = "banknote_events"
    __table_args__ = (UniqueConstraint("user_id", "request_id", name="uq_banknote_event_user_request"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    banknote_id: Mapped[int] = mapped_column(ForeignKey("banknotes.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    city: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(Text)
    image: Mapped[str | None] = mapped_column(Text)
    is_hidden: Mapped[bool]
    request_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Deal(Base):
    __tablename__ = "deals"
    __table_args__ = (
        CheckConstraint("sale_minor >= 0 AND original_minor > sale_minor", name="ck_deal_sale_price"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store: Mapped[str] = mapped_column(String(80))
    product: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(24))
    city: Mapped[str] = mapped_column(String(80))
    currency: Mapped[str] = mapped_column(String(3))
    original_minor: Mapped[int]
    sale_minor: Mapped[int]
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    expires_on: Mapped[date | None] = mapped_column(Date)
