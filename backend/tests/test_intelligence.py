from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4

from app.models import Transaction
from app.recurring_detection import analyze


def sign_in(client, username):
    credentials = {"email": f"{username}@example.com", "password": "safe-password"}
    assert client.post("/api/auth/register", json={**credentials, "username": username}).status_code == 201
    token = client.post("/api/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def add_operation(client, headers, kind, amount, **fields):
    response = client.post("/api/banking/operations", headers=headers, json={
        "operation_id": str(uuid4()), "transaction_type": kind,
        "account_type": "chequing", "amount_minor": amount, **fields,
    })
    assert response.status_code == 204
    return response.headers["X-Transaction-Id"]


def test_audit_rating_history_privacy_and_reset(client):
    owner = sign_in(client, "owner")
    stranger = sign_in(client, "stranger")
    deposit = add_operation(client, owner, "deposit", 50_000)
    purchase = add_operation(client, owner, "purchase", 25_000, merchant_name="Bike Shop", category="Shopping")
    path = f"/api/audits/{purchase}"
    assert client.get(path).status_code == 401
    assert client.get(f"/api/audits/{deposit}", headers=owner).status_code == 404
    assert client.get(path, headers=stranger).status_code == 404
    assert client.put(path, headers=stranger, json={"necessity_rating": 7}).status_code == 404
    assert client.get(path, headers=owner).json()["audit"] is None
    assert client.put(path, headers=owner, json={"necessity_rating": 0}).status_code == 422

    saved = client.put(path, headers=owner, json={"necessity_rating": 7, "reflection": "  Check used options. "})
    assert saved.status_code == 200
    assert saved.json()["audit"] == {"necessity_rating": 7, "reflection": "Check used options."}
    assert any("refurbished" in text for text in saved.json()["alternatives"])
    assert client.put(path, headers=owner, json={"necessity_rating": 6}).status_code == 200
    history = client.get("/api/audits", headers=owner).json()
    assert len(history["items"]) == 1
    assert history["items"][0]["audit"] == {"necessity_rating": 6, "reflection": None}
    assert client.get("/api/audits", headers=stranger).json()["items"] == []
    assert client.post("/api/banking/reset", headers=owner).status_code == 204
    assert client.get(path, headers=owner).status_code == 404
    assert client.get("/api/audits", headers=owner).json()["items"] == []


def test_audit_projects_owned_purchase_against_owned_goal(client):
    owner = sign_in(client, "owner")
    other = sign_in(client, "other")
    add_operation(client, owner, "deposit", 50_000)
    purchase = add_operation(client, owner, "purchase", 25_000, merchant_name="Shop", category="Shopping")
    data = {"name": "Trip", "target_minor": 200_000, "monthly_minor": 40_000}
    own_goal = client.post("/api/goals", headers=owner, json=data).json()["id"]
    other_goal = client.post("/api/goals", headers=other, json=data).json()["id"]
    path = f"/api/audits/{purchase}/projection"
    projection = client.get(f"{path}/{own_goal}", headers=owner).json()
    assert projection["baseline"]["periods"] == 5
    assert projection["with_purchase"]["periods"] == 6
    assert projection["delay_days"] == 30
    assert client.get(f"{path}/{other_goal}", headers=owner).status_code == 404
    assert client.get(f"{path}/{other_goal}", headers=other).status_code == 404


def test_demo_report_is_private_and_reconciles_annual_estimates(client):
    owner = sign_in(client, "owner")
    other = sign_in(client, "other")
    assert client.get("/api/money-leaks").status_code == 401
    assert client.post("/api/banking/demo", headers=owner).status_code == 204
    report = client.get("/api/money-leaks", headers=owner).json()
    by_merchant = {item["merchant"]: item for item in report["recurring"]}
    assert by_merchant["Stream View"]["cadence"] == "Monthly"
    assert by_merchant["Stream View"]["annual_minor"] == 1699 * 12
    assert by_merchant["Stream View"]["previous_amount_minor"] == 1299
    assert by_merchant["City Fitness"]["cadence"] == "Weekly"
    assert report["potential_annual_savings_minor"] == (1699 * 12) + (799 * 52)
    assert report["potential_annual_increase_minor"] == 4800
    assert [(item["merchant"], item["count"]) for item in report["duplicates"]] == [("Corner Cafe", 2)]
    assert client.get("/api/money-leaks", headers=other).json()["recurring"] == []


def test_same_day_duplicates_do_not_count_as_recurrences_and_stale_is_excluded():
    today = date(2026, 11, 22)

    def entry(name, age, amount):
        return Transaction(
            merchant_name=name, created_at=datetime.combine(today - timedelta(days=age), time.min, timezone.utc),
            amount_minor=-amount, category="Other", transaction_type="bill",
        )

    report = analyze([
        entry("Old Pass", 90, 1000), entry("OLD-PASS", 84, 1000), entry("Old pass", 76, 1000),
        entry("Cafe", 0, 500), entry("CAFE", 0, 500), entry("cafe", 0, 500),
        entry("Variable Store", 14, 1000), entry("Variable Store", 7, 1800), entry("Variable Store", 0, 1200),
    ], today)
    assert len(report.recurring) == 1
    assert not report.recurring[0].active
    assert report.potential_annual_savings_minor == 0
    assert report.duplicates[0].count == 3


def test_operation_retry_returns_same_audit_link_target(client):
    headers = sign_in(client, "buyer")
    add_operation(client, headers, "deposit", 5000)
    body = {
        "operation_id": str(uuid4()), "transaction_type": "purchase", "account_type": "chequing",
        "amount_minor": 1025, "merchant_name": "Shop", "category": "Shopping",
    }
    first = client.post("/api/banking/operations", headers=headers, json=body)
    second = client.post("/api/banking/operations", headers=headers, json=body)
    assert first.status_code == second.status_code == 204
    assert first.headers["X-Transaction-Id"] == second.headers["X-Transaction-Id"]
    assert client.get(f"/api/audits/{first.headers['X-Transaction-Id']}", headers=headers).status_code == 200
