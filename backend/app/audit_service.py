from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit_schemas import AuditedPurchase, AuditHistory, AuditInput
from .banking_service import lock_user
from .models import Transaction, TransactionAudit

ALTERNATIVES = {
    "Food": ("Compare unit prices or try a store-brand equivalent.", "For takeout, compare pickup prices or plan a meal at home."),
    "Shopping": ("Check second-hand or refurbished options with a return policy.", "Compare the total cost at another retailer or wait for a sale."),
    "Transport": ("Compare a transit pass, single fares, and carpooling for the same trip.",),
    "Housing": ("Compare quotes for the same scope before committing to a future expense.",),
    "Utilities": ("Review your plan and compare lower tiers with equivalent coverage.",),
    "Entertainment": ("Consider a library, community event, or a lower-priced plan.", "Check whether you can use a service you already pay for."),
    "Other": ("Compare prices for a comparable option before buying again.", "Consider borrowing, renting, or waiting for a sale."),
}


class PurchaseNotFound(Exception):
    pass


def owned_purchase(db: Session, user_id: int, transaction_id: int) -> Transaction:
    purchase = db.scalar(select(Transaction).where(
        Transaction.id == transaction_id, Transaction.user_id == user_id, Transaction.transaction_type == "purchase",
    ))
    if purchase is None:
        raise PurchaseNotFound
    return purchase


def view(purchase: Transaction, audit: TransactionAudit | None) -> AuditedPurchase:
    return AuditedPurchase(
        purchase=purchase, audit=audit, alternatives=list(ALTERNATIVES.get(purchase.category, ALTERNATIVES["Other"])),
    )


def find_audit(db: Session, purchase: Transaction) -> TransactionAudit | None:
    return db.scalar(select(TransactionAudit).where(
        TransactionAudit.transaction_id == purchase.id, TransactionAudit.user_id == purchase.user_id,
    ))


def detail(db: Session, user_id: int, transaction_id: int) -> AuditedPurchase:
    purchase = owned_purchase(db, user_id, transaction_id)
    return view(purchase, find_audit(db, purchase))


def save(db: Session, user_id: int, transaction_id: int, data: AuditInput) -> AuditedPurchase:
    lock_user(db, user_id)
    purchase = owned_purchase(db, user_id, transaction_id)
    audit = find_audit(db, purchase)
    if audit is None:
        audit = TransactionAudit(transaction_id=purchase.id, user_id=user_id)
        db.add(audit)
    audit.necessity_rating = data.necessity_rating
    audit.reflection = data.reflection or None
    result = view(purchase, audit)
    db.commit()
    return result


def history(db: Session, user_id: int, before_id: int | None, limit: int = 20) -> AuditHistory:
    statement = select(Transaction, TransactionAudit).join(
        TransactionAudit, TransactionAudit.transaction_id == Transaction.id,
    ).where(Transaction.user_id == user_id, TransactionAudit.user_id == user_id)
    if before_id is not None:
        statement = statement.where(TransactionAudit.id < before_id)
    rows = db.execute(statement.order_by(TransactionAudit.id.desc()).limit(limit + 1)).all()
    return AuditHistory(
        items=[view(purchase, audit) for purchase, audit in rows[:limit]],
        before_id=rows[limit - 1][1].id if len(rows) > limit else None,
    )
