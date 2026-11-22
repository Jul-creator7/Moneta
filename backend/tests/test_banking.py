from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def authenticate(client, username="spender"):
    credentials = {"email": f"{username}@example.com", "password": "safe-password"}
    user = client.post("/api/auth/register", json={**credentials, "username": username})
    assert user.status_code == 201
    token = client.post("/api/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def write(client, headers, kind, amount, **fields):
    return client.post("/api/banking/operations", headers=headers, json={
        "operation_id": str(uuid4()),
        "transaction_type": kind,
        "account_type": "chequing",
        "amount_minor": amount,
        **fields,
    })


def dashboard(client, headers):
    response = client.get("/api/banking/dashboard", headers=headers)
    assert response.status_code == 200
    return response.json()


def test_migration_backfills_existing_accounts(tmp_path):
    path = tmp_path / "legacy.db"
    url = f"sqlite:///{path}"
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.attributes["database_url"] = url
    command.upgrade(config, "0001")
    engine = create_engine(url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO users (email, username, password_hash) VALUES ('old@example.com', 'old', 'test-hash')"))
        db.execute(text(
            "INSERT INTO bank_accounts (user_id, account_type, name, currency) "
            "VALUES (1, 'savings', 'Original savings', 'CAD')"
        ))
    command.upgrade(config, "head")
    with engine.connect() as db:
        assert db.execute(text("SELECT account_type, name, balance_minor FROM bank_accounts ORDER BY account_type")).all() == [
            ("chequing", "Chequing", 0), ("savings", "Original savings", 0),
        ]
    assert inspect(engine).has_table("transactions")
    engine.dispose()


def test_post_operations_and_dashboard(client):
    headers = authenticate(client)
    assert [account["balance_minor"] for account in dashboard(client, headers)["accounts"]] == [0, 0]
    assert write(client, headers, "deposit", 8000).status_code == 204
    assert write(client, headers, "income", 10000).status_code == 204
    assert write(client, headers, "purchase", 1299, merchant_name="Store", category="Food").status_code == 204
    assert write(client, headers, "bill", 2001, merchant_name="Internet", category="Utilities").status_code == 204
    assert write(client, headers, "transfer", 1000, destination="savings").status_code == 204
    data = dashboard(client, headers)
    assert data["total_balance_minor"] == 14700
    assert data["savings_balance_minor"] == 1000
    assert data["monthly_income_minor"] == 10000
    assert data["monthly_spending_minor"] == 3300
    assert data["monthly_savings_rate"] == 67
    assert data["spending_by_category"] == [
        {"category": "Utilities", "total_minor": 2001}, {"category": "Food", "total_minor": 1299},
    ]
    transfers = [entry for entry in data["recent_transactions"] if entry["transaction_type"] == "transfer"]
    assert len(transfers) == 2
    assert transfers[0]["transfer_group_id"] == transfers[1]["transfer_group_id"]
    assert sorted(entry["amount_minor"] for entry in transfers) == [-1000, 1000]


def test_retry_and_failed_transfer_do_not_mutate_ledger(client):
    headers = authenticate(client)
    key = str(uuid4())
    assert write(client, headers, "deposit", 100, operation_id=key).status_code == 204
    assert write(client, headers, "deposit", 100, operation_id=key).status_code == 204
    assert write(client, headers, "deposit", 101, operation_id=key).status_code == 409
    assert write(client, headers, "transfer", 101, destination="savings").status_code == 409
    assert write(client, headers, "transfer", 10, destination="chequing").status_code == 422
    assert write(client, headers, "purchase", 1, merchant_name="Store").status_code == 422
    assert write(client, headers, "deposit", 1.5).status_code == 422
    data = dashboard(client, headers)
    assert len(data["recent_transactions"]) == 1
    assert data["total_balance_minor"] == 100
    assert data["savings_balance_minor"] == 0


def test_concurrent_debits_do_not_overdraw(client):
    headers = authenticate(client)
    assert write(client, headers, "deposit", 100).status_code == 204
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(
            lambda _: write(client, headers, "transfer", 75, destination="savings").status_code, range(2)
        ))
    assert sorted(results) == [204, 409]
    assert [account["balance_minor"] for account in dashboard(client, headers)["accounts"]] == [25, 75]


def test_demo_history_reset_and_isolation(client):
    first = authenticate(client, "first")
    second = authenticate(client, "second")
    assert client.get("/api/banking/dashboard").status_code == 401
    assert client.get("/api/banking/transactions").status_code == 401
    assert client.post("/api/banking/demo", headers=first).status_code == 204
    assert client.post("/api/banking/demo", headers=first).status_code == 409
    assert dashboard(client, second)["total_balance_minor"] == 0
    assert client.get("/api/banking/transactions", headers=second).json()["transactions"] == []
    page = client.get("/api/banking/transactions?limit=3", headers=first).json()
    assert len(page["transactions"]) == 3
    assert page["next_offset"] == 3
    remaining = client.get("/api/banking/transactions?limit=10&offset=3", headers=first).json()
    assert len(remaining["transactions"]) == 4
    assert remaining["next_offset"] is None
    assert {entry["id"] for entry in page["transactions"]}.isdisjoint(entry["id"] for entry in remaining["transactions"])
    assert client.post("/api/banking/reset", headers=second).status_code == 204
    assert dashboard(client, first)["total_balance_minor"] > 0
    assert client.post("/api/banking/reset", headers=first).status_code == 204
    cleared = dashboard(client, first)
    assert cleared["total_balance_minor"] == 0
    assert cleared["recent_transactions"] == []
