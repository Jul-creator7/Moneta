from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from unicodedata import normalize

from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit_schemas import MoneyLeaksReport, PossibleDuplicate, RecurringCharge
from .banking_service import EXPENSE_TYPES
from .models import Transaction

Cadence = Literal["Weekly", "Monthly"]
CADENCES: tuple[tuple[Cadence, int, int, int, int], ...] = (
    ("Weekly", 5, 9, 52, 14),
    ("Monthly", 25, 35, 12, 50),
)


def merchant_key(name: str) -> str:
    return "".join(char for char in normalize("NFKC", name).casefold() if char.isalnum())


def recurring_group(charges: list[Transaction], today: date) -> RecurringCharge | None:
    by_date: dict[date, Transaction] = {}
    for charge in charges:
        by_date.setdefault(charge.created_at.date(), charge)
    days = sorted(by_date)
    if len(days) < 3:
        return None

    # Search from the latest charge for the most recent three consistent dates.
    # A stray purchase from the same merchant between those dates can be skipped.
    for index in range(len(days) - 1, 1, -1):
        latest_day = days[index]
        for cadence, minimum, maximum, annual_count, stale_after in CADENCES:
            earliest = bisect_left(days, latest_day - timedelta(days=maximum))
            latest_middle = bisect_right(days, latest_day - timedelta(days=minimum))
            for middle in reversed(days[earliest:latest_middle]):
                prior = -by_date[middle].amount_minor
                amount = -by_date[latest_day].amount_minor
                # Avoid merging unrelated purchases whose prices differ widely.
                if max(prior, amount) > 2 * min(prior, amount):
                    continue
                start = bisect_left(days, middle - timedelta(days=maximum))
                end = bisect_right(days, middle - timedelta(days=minimum))
                older_amounts = (-by_date[day].amount_minor for day in reversed(days[start:end]))
                oldest = next((value for value in older_amounts if abs(prior - value) * 100 <= max(prior, value) * 20), None)
                if oldest is None:
                    continue
                latest = by_date[latest_day]
                prior_stable = abs(prior - oldest) * 100 <= max(prior, oldest) * 5
                increase = amount - prior
                active = (today - latest_day).days <= stale_after
                price_change = prior_stable and increase > 0 and (increase >= 100 or increase * 100 >= prior * 10)
                return RecurringCharge(
                    merchant=latest.merchant_name, category=latest.category, cadence=cadence, last_charged=latest_day,
                    amount_minor=amount, annual_minor=amount * annual_count, active=active,
                    previous_amount_minor=prior if price_change else None,
                    annual_increase_minor=increase * annual_count if price_change else 0,
                )
    return None


def analyze(entries: list[Transaction], today: date) -> MoneyLeaksReport:
    recurring_groups: dict[tuple[str, str], list[Transaction]] = defaultdict(list)
    duplicate_groups: dict[tuple[str, date, int], list[Transaction]] = defaultdict(list)
    for entry in entries:
        if not entry.merchant_name or entry.amount_minor >= 0 or entry.transaction_type not in EXPENSE_TYPES:
            continue
        merchant = merchant_key(entry.merchant_name)
        if not merchant:
            continue
        recurring_groups[(merchant, entry.category)].append(entry)
        duplicate_groups[(merchant, entry.created_at.date(), -entry.amount_minor)].append(entry)

    recurring = [result for group in recurring_groups.values() if (result := recurring_group(group, today)) is not None]
    recurring.sort(key=lambda item: (not item.active, -item.annual_minor, item.merchant))
    duplicates = [
        PossibleDuplicate(merchant=group[0].merchant_name, charged_on=day, amount_minor=amount, count=len(group))
        for (_, day, amount), group in duplicate_groups.items() if len(group) > 1
    ]
    duplicates.sort(key=lambda item: (item.charged_on, item.amount_minor), reverse=True)
    return MoneyLeaksReport(
        recurring=recurring,
        duplicates=duplicates,
        potential_annual_savings_minor=sum(item.annual_minor for item in recurring if item.active),
        potential_annual_increase_minor=sum(item.annual_increase_minor for item in recurring if item.active),
    )


def report(db: Session, user_id: int) -> MoneyLeaksReport:
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today - timedelta(days=364), time.min, timezone.utc)
    end = datetime.combine(today + timedelta(days=1), time.min, timezone.utc)
    entries = db.scalars(select(Transaction).where(
        Transaction.user_id == user_id, Transaction.transaction_type.in_(EXPENSE_TYPES),
        Transaction.created_at >= start, Transaction.created_at < end,
    ).order_by(Transaction.created_at, Transaction.id)).all()
    return analyze(entries, today)
