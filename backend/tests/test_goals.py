from concurrent.futures import ThreadPoolExecutor
from datetime import date
from uuid import uuid4

from app.goal_service import timeline


def sign_in(client, username):
    credentials = {"email": f"{username}@example.com", "password": "safe-password"}
    assert client.post("/api/auth/register", json={**credentials, "username": username}).status_code == 201
    token = client.post("/api/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def goal(client, headers, name="Emergency fund", monthly=40_000):
    response = client.post("/api/goals", headers=headers, json={
        "name": name, "target_minor": 300_000, "monthly_minor": monthly, "target_date": "2030-06-15",
    })
    assert response.status_code == 201
    return response.json()


def allocate(client, headers, goal_id, amount):
    return client.put(f"/api/goals/{goal_id}/allocation", headers=headers, json={"allocated_minor": amount})


def bank(client, headers, kind, amount, **fields):
    return client.post("/api/banking/operations", headers=headers, json={
        "operation_id": str(uuid4()), "transaction_type": kind,
        "account_type": "savings", "amount_minor": amount, **fields,
    })


def project(client, headers, goal_id, amount=25_000, funding="allocated"):
    return client.post(f"/api/goals/{goal_id}/projection", headers=headers, json={
        "amount_minor": amount, "funding": funding,
    })


def overview(client, headers):
    response = client.get("/api/goals", headers=headers)
    assert response.status_code == 200
    return response.json()


def test_goal_funding_and_release_obey_savings_balance(client):
    headers = sign_in(client, "saver")
    first = goal(client, headers)["id"]
    second = goal(client, headers, "Vacation")["id"]
    assert allocate(client, headers, first, 1).status_code == 409
    assert bank(client, headers, "deposit", 100_000).status_code == 204
    assert allocate(client, headers, first, 80_000).status_code == 200
    assert allocate(client, headers, first, 80_000).status_code == 200
    assert allocate(client, headers, second, 20_001).status_code == 409
    assert bank(client, headers, "transfer", 20_001, destination="chequing").status_code == 409
    assert bank(client, headers, "purchase", 20_001, merchant_name="Store", category="Food").status_code == 409
    assert overview(client, headers)["unallocated_minor"] == 20_000
    assert allocate(client, headers, first, 30_000).status_code == 200
    assert allocate(client, headers, second, 20_000).status_code == 200
    assert bank(client, headers, "transfer", 50_000, destination="chequing").status_code == 204
    assert overview(client, headers)["unallocated_minor"] == 0
    assert client.post("/api/banking/reset", headers=headers).status_code == 204
    result = overview(client, headers)
    assert result["savings_minor"] == result["unallocated_minor"] == 0
    assert [item["allocated_minor"] for item in result["goals"]] == [0, 0]


def test_concurrent_allocation_and_savings_debit_are_serialized(client):
    headers = sign_in(client, "racer")
    goal_id = goal(client, headers)["id"]
    assert bank(client, headers, "deposit", 100).status_code == 204
    with ThreadPoolExecutor(max_workers=2) as workers:
        funding = workers.submit(allocate, client, headers, goal_id, 75)
        debit = workers.submit(bank, client, headers, "transfer", 75, destination="chequing")
        assert {funding.result().status_code, debit.result().status_code} in ({200, 409}, {204, 409})
    assert overview(client, headers)["unallocated_minor"] == 25


def test_projection_both_funding_options_and_no_mutation(client):
    headers = sign_in(client, "planner")
    goal_id = goal(client, headers)["id"]
    assert bank(client, headers, "deposit", 100_000).status_code == 204
    assert allocate(client, headers, goal_id, 100_000).status_code == 200
    for funding, start in (("allocated", 75_000), ("contributions", 100_000)):
        response = project(client, headers, goal_id, funding=funding)
        assert response.status_code == 200
        result = response.json()
        assert result["baseline"]["periods"] == 5
        assert result["with_purchase"]["periods"] == 6
        assert result["with_purchase"]["starting_minor"] == start
        assert result["delay_days"] == 30
        baseline = date.fromisoformat(result["baseline"]["estimated_date"])
        end = date.fromisoformat(result["with_purchase"]["estimated_date"])
        assert (end - baseline).days == 30
    assert project(client, headers, goal_id, amount=100_001).status_code == 409
    carry = project(client, headers, goal_id, amount=90_001, funding="contributions").json()
    assert carry["delay_days"] == 90
    assert overview(client, headers)["goals"][0]["allocated_minor"] == 100_000


def test_plan_edits_and_projection_edge_cases(client):
    headers = sign_in(client, "editor")
    original = goal(client, headers, monthly=0)
    goal_id = original["id"]
    result = project(client, headers, goal_id, funding="contributions").json()
    assert result["baseline"]["estimated_date"] is None
    assert result["delay_days"] is None
    assert bank(client, headers, "deposit", 300_000).status_code == 204
    assert allocate(client, headers, goal_id, 300_000).status_code == 200
    complete = project(client, headers, goal_id, funding="contributions").json()
    assert complete["baseline"]["estimated_date"] == complete["as_of"]
    assert complete["delay_days"] == 0
    assert project(client, headers, goal_id).json()["with_purchase"]["periods"] is None
    edited = {"name": "Updated", "target_minor": 299_999, "monthly_minor": 50_000}
    assert client.put(f"/api/goals/{goal_id}", headers=headers, json=edited).status_code == 409
    edited["target_minor"] = 320_000
    assert client.put(f"/api/goals/{goal_id}", headers=headers, json=edited).json()["monthly_minor"] == 50_000
    assert timeline(date(2026, 11, 22), 0, 100_000_000, 1).estimated_date is None


def test_goals_are_private(client):
    first = sign_in(client, "first")
    second = sign_in(client, "second")
    goal_id = goal(client, first)["id"]
    assert client.get("/api/goals").status_code == 401
    assert overview(client, second)["goals"] == []
    assert allocate(client, second, goal_id, 0).status_code == 404
    assert project(client, second, goal_id, funding="contributions").status_code == 404
    assert client.put(f"/api/goals/{goal_id}", headers=second, json={
        "name": "Update", "target_minor": 100, "monthly_minor": 10,
    }).status_code == 404


def test_local_cors_allows_authenticated_goal_updates(client):
    response = client.options("/api/goals/1/allocation", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "PUT",
        "Access-Control-Request-Headers": "authorization, content-type",
    })
    assert response.status_code == 200
    assert "PUT" in response.headers["Access-Control-Allow-Methods"]
