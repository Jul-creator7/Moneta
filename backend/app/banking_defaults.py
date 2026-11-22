from sqlalchemy.orm import Session

from .models import BankAccount

CURRENCY = "CAD"
ACCOUNT_NAMES = {"chequing": "Chequing", "savings": "Savings"}


def provision_accounts(db: Session, user_id: int) -> None:
    db.add_all(
        BankAccount(user_id=user_id, account_type=kind, name=name, currency=CURRENCY)
        for kind, name in ACCOUNT_NAMES.items()
    )
