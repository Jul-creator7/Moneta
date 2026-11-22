from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from .banking_defaults import CURRENCY
from .banking_schemas import CategoryTotal, Dashboard, History, Operation
from .models import BankAccount, SavingsGoal, Transaction, User

EXPENSE_TYPES = ("purchase", "bill")
MAX_BALANCE_MINOR = 100_000_000_000
DESCRIPTION = {
    "deposit": "Simulated deposit",
    "income": "Simulated income",
    "purchase": "Simulated purchase",
    "bill": "Simulated bill payment",
    "transfer": "Internal transfer",
}


class BankingConflict(Exception):
    pass


def accounts_for(db: Session, user_id: int) -> dict[str, BankAccount]:
    accounts = db.scalars(select(BankAccount).where(
        BankAccount.user_id == user_id,
        BankAccount.currency == CURRENCY,
        BankAccount.account_type.in_(("chequing", "savings")),
    ).order_by(BankAccount.account_type))
    return {account.account_type: account for account in accounts}


def lock_user(db: Session, user_id: int) -> None:
    # Acquire the write lock before reading balances. SQLite serializes writes,
    # while PostgreSQL locks this user's row for the duration of the transaction.
    db.execute(update(User).where(User.id == user_id).values(id=User.id))


def post_entries(
    db: Session, accounts: dict[str, BankAccount], operation: Operation, created_at: datetime,
) -> Transaction:
    kind = operation.transaction_type
    source = accounts[operation.account_type]
    amount = operation.amount_minor
    debits_source = kind in EXPENSE_TYPES or kind == "transfer"
    legs = [(source, -amount if debits_source else amount)]
    if operation.destination is not None:
        legs.append((accounts[operation.destination], amount))

    for account, delta in legs:
        balance = account.balance_minor + delta
        if balance < 0:
            raise BankingConflict("Insufficient funds in this simulated account.")
        if account.account_type == "savings" and delta < 0:
            allocated = db.scalar(select(func.coalesce(func.sum(SavingsGoal.allocated_minor), 0)).where(
                SavingsGoal.user_id == account.user_id,
            ))
            if balance < allocated:
                raise BankingConflict("Release savings allocated to goals before using these funds.")
        if balance > MAX_BALANCE_MINOR:
            raise BankingConflict("This operation exceeds the simulated account limit.")

    operation_id = str(operation.operation_id)
    entries = []
    for account, delta in legs:
        account.balance_minor += delta
        entries.append(Transaction(
            user_id=account.user_id,
            account_id=account.id,
            amount_minor=delta,
            transaction_type=kind,
            merchant_name=operation.merchant_name,
            category=operation.category or kind.capitalize(),
            description=operation.description or DESCRIPTION[kind],
            operation_id=operation_id,
            transfer_group_id=operation_id if kind == "transfer" else None,
            created_at=created_at,
        ))
    db.add_all(entries)
    return entries[0]


def record(db: Session, user_id: int, operation: Operation) -> int:
    lock_user(db, user_id)
    accounts = accounts_for(db, user_id)
    previous = db.scalars(select(Transaction).where(
        Transaction.user_id == user_id,
        Transaction.operation_id == str(operation.operation_id),
    )).all()
    if previous:
        by_account = {entry.account_id: entry for entry in previous}
        source = by_account.get(accounts[operation.account_type].id)
        destination = accounts.get(operation.destination) if operation.destination else None
        signed_amount = -operation.amount_minor if operation.transaction_type in (*EXPENSE_TYPES, "transfer") else operation.amount_minor
        if (
            source is None
            or len(previous) != (2 if destination else 1)
            or (destination is not None and destination.id not in by_account)
            or source.amount_minor != signed_amount
            or source.transaction_type != operation.transaction_type
            or source.merchant_name != operation.merchant_name
            or source.category != (operation.category or operation.transaction_type.capitalize())
            or source.description != (operation.description or DESCRIPTION[operation.transaction_type])
        ):
            raise BankingConflict("This request ID was already used for a different operation.")
    else:
        source = post_entries(db, accounts, operation, datetime.now(timezone.utc))
        db.flush()
    transaction_id = source.id
    db.commit()
    return transaction_id


def history(db: Session, user_id: int, offset: int, limit: int) -> History:
    entries = db.scalars(select(Transaction).where(Transaction.user_id == user_id)
        .order_by(Transaction.created_at.desc(), Transaction.id.desc()).offset(offset).limit(limit + 1)).all()
    return History(transactions=entries[:limit], next_offset=offset + limit if len(entries) > limit else None)


def dashboard(db: Session, user_id: int) -> Dashboard:
    accounts = accounts_for(db, user_id)
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = (start + timedelta(days=32)).replace(day=1)
    types = (*EXPENSE_TYPES, "income")
    totals = db.execute(select(
        Transaction.transaction_type, Transaction.category, func.sum(Transaction.amount_minor),
    ).where(
        Transaction.user_id == user_id,
        Transaction.created_at >= start,
        Transaction.created_at < end,
        Transaction.transaction_type.in_(types),
    ).group_by(Transaction.transaction_type, Transaction.category))
    income = 0
    categories: dict[str, int] = {}
    for kind, category, amount in totals:
        if kind == "income":
            income += amount
        else:
            categories[category] = categories.get(category, 0) - amount
    spending = sum(categories.values())
    return Dashboard(
        accounts=list(accounts.values()),
        total_balance_minor=sum(account.balance_minor for account in accounts.values()),
        savings_balance_minor=accounts["savings"].balance_minor,
        monthly_income_minor=income,
        monthly_spending_minor=spending,
        monthly_savings_rate=round((income - spending) * 100 / income, 1) if income else None,
        spending_by_category=[
            CategoryTotal(category=category, total_minor=amount)
            for category, amount in sorted(categories.items(), key=lambda item: (-item[1], item[0]))
        ],
        recent_transactions=history(db, user_id, 0, 6).transactions,
    )


def load_demo(db: Session, user_id: int) -> None:
    lock_user(db, user_id)
    accounts = accounts_for(db, user_id)
    if any(account.balance_minor for account in accounts.values()) or db.scalar(
        select(Transaction.id).where(Transaction.user_id == user_id).limit(1)
    ) is not None:
        raise BankingConflict("Reset your simulation before loading the demo again.")
    now = datetime.now(timezone.utc)
    sample = [
        ("income", 245000, None, None, "Demo paycheque", None),
        ("purchase", 11248, "Market Grocer", "Food", "Demo groceries", None),
        ("bill", 6899, "Northline Internet", "Utilities", "Demo internet bill", None),
        ("purchase", 4500, "City Transit", "Transport", "Demo transit pass", None),
        ("purchase", 2850, "Studio Cinema", "Entertainment", "Demo movie night", None),
        ("transfer", 50000, None, None, "Demo savings transfer", "savings"),
    ]
    for kind, amount, merchant, category, description, destination in sample:
        post_entries(db, accounts, Operation(
            operation_id=uuid4(), transaction_type=kind, account_type="chequing",
            amount_minor=amount, merchant_name=merchant, category=category,
            description=description, destination=destination,
        ), now)
    history = [
        (90, "income", 145000, None, None, "Demo historical paycheque"),
        (65, "bill", 1299, "Stream View", "Entertainment", "Demo streaming subscription"),
        (35, "bill", 1299, "STREAM-VIEW", "Entertainment", "Demo streaming subscription"),
        (5, "bill", 1699, "Stream View", "Entertainment", "Demo streaming subscription"),
        (17, "bill", 799, "City Fitness", "Other", "Demo weekly membership"),
        (10, "bill", 799, "City Fitness", "Other", "Demo weekly membership"),
        (3, "bill", 799, "City Fitness", "Other", "Demo weekly membership"),
        (2, "purchase", 1450, "Corner Cafe", "Food", "Demo cafe payment"),
        (2, "purchase", 1450, "Corner Cafe", "Food", "Demo cafe payment"),
    ]
    for days, kind, amount, merchant, category, description in history:
        post_entries(db, accounts, Operation(
            operation_id=uuid4(), transaction_type=kind, account_type="chequing",
            amount_minor=amount, merchant_name=merchant, category=category, description=description,
        ), now - timedelta(days=days))
    db.commit()


def reset(db: Session, user_id: int) -> None:
    lock_user(db, user_id)
    db.execute(delete(Transaction).where(Transaction.user_id == user_id))
    db.execute(update(SavingsGoal).where(SavingsGoal.user_id == user_id).values(allocated_minor=0))
    for account in accounts_for(db, user_id).values():
        account.balance_minor = 0
    db.commit()
