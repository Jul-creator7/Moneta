from fastapi import APIRouter, HTTPException, Request

from . import audit_service, banking_service, recurring_detection
from .banking_api import CurrentUser, Database
from .coach_service import CoachReply, advise

router = APIRouter(prefix="/coach", tags=["coach"])


@router.post("/spending", response_model=CoachReply)
def spending(request: Request, user: CurrentUser, db: Database):
    dashboard = banking_service.dashboard(db, user.id)
    categories = dashboard.spending_by_category[:5]
    if not categories:
        return CoachReply(source="local", tips=["Record a simulated purchase or bill to see suggestions based on your spending."])
    context = {
        "topic": "month-to-date spending",
        "income_minor": dashboard.monthly_income_minor,
        "spending_minor": dashboard.monthly_spending_minor,
        "top_categories": [item.model_dump() for item in categories],
        "currency": "CAD",
    }
    return advise(request.app.state.settings, request.app.state.coach_budget, user.id, context, [
        f"{categories[0].category} is your largest spending category so far this month. Review it for one expense you could reduce or replace.",
        "Set an amount you want to save and check it against your spending at the end of the month.",
    ])


@router.post("/recurring", response_model=CoachReply)
def recurring(request: Request, user: CurrentUser, db: Database):
    report = recurring_detection.report(db, user.id)
    active = sum(item.active for item in report.recurring)
    if active == 0:
        return CoachReply(source="local", tips=["Review your statements for recurring services and compare them again after more simulated activity."])
    context = {
        "topic": "recurring spending review",
        "active_patterns": active,
        "potential_duplicate_groups": len(report.duplicates),
        "potential_annual_cost_minor": report.potential_annual_savings_minor,
        "potential_annual_increase_minor": report.potential_annual_increase_minor,
        "currency": "CAD",
    }
    return advise(request.app.state.settings, request.app.state.coach_budget, user.id, context, [
        "Start with services you rarely use. Confirm billing terms and check for a lower tier before cancelling.",
        "Compare suspected duplicates with your receipts and check whether any price changes match a plan change.",
    ])


@router.post("/purchases/{transaction_id}", response_model=CoachReply)
def purchase(transaction_id: int, request: Request, user: CurrentUser, db: Database):
    try:
        detail = audit_service.detail(db, user.id, transaction_id)
    except audit_service.PurchaseNotFound as error:
        raise HTTPException(404, "Purchase not found.") from error
    context = {
        "topic": "lower-cost options for a similar purchase",
        "category": detail.purchase.category,
        "necessity_rating": detail.audit.necessity_rating if detail.audit else None,
    }
    return advise(request.app.state.settings, request.app.state.coach_budget, user.id, context, detail.alternatives)
