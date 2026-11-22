import io
import json
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app import coach_service
from app.config import Settings
from app.main import create_app


def create_member(client, username):
    credentials = {"email": f"{username}@example.com", "password": "safe-password"}
    assert client.post("/api/auth/register", json={**credentials, "username": username}).status_code == 201
    login = client.post("/api/auth/login", json=credentials)
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_coach_sends_only_explicit_summary_and_falls_back(client, monkeypatch):
    config = client.app.state.settings
    config.openai_api_key = None
    owner = create_member(client, "owner")
    other = create_member(client, "other")
    assert client.post("/api/coach/spending").status_code == 401
    assert client.post("/api/banking/demo", headers=owner).status_code == 204
    history = client.get("/api/banking/transactions", headers=owner).json()["transactions"]
    purchase_id = next(item["id"] for item in history if item["transaction_type"] == "purchase")
    audit_path = f"/api/audits/{purchase_id}"
    coach_path = f"/api/coach/purchases/{purchase_id}"
    assert client.put(audit_path, headers=owner, json={
        "necessity_rating": 5, "reflection": "Do not share this private note.",
    }).status_code == 200
    assert client.post(coach_path, headers=other).status_code == 404
    assert client.post(coach_path, headers=owner).json()["source"] == "local"

    requests = []

    def reply(request, timeout):
        payload = json.loads(request.data)
        requests.append(payload)
        assert request.full_url == coach_service.OPENAI_RESPONSES_URL
        assert timeout == 6
        return io.BytesIO(json.dumps({
            "status": "completed", "output": [{
                "type": "message", "content": [{
                    "type": "output_text", "text": json.dumps({"tips": ["Compare total costs across options."]}),
                }],
            }],
        }).encode())

    config.openai_api_key = SecretStr("mock-provider-key")
    monkeypatch.setattr(coach_service, "urlopen", reply)
    assert client.post(coach_path, headers=owner).json() == {
        "source": "ai", "tips": ["Compare total costs across options."],
    }
    context = json.loads(requests[0]["input"])
    assert set(context) == {"topic", "category", "necessity_rating"}
    assert context["necessity_rating"] == 5
    assert requests[0]["store"] is False

    def unavailable(*args, **kwargs):
        raise TimeoutError

    monkeypatch.setattr(coach_service, "urlopen", unavailable)
    assert client.post("/api/coach/recurring", headers=owner).json()["source"] == "local"
    monkeypatch.setattr(coach_service, "urlopen", reply)
    assert client.post("/api/coach/spending", headers=owner).json()["source"] == "local"
    assert len(requests) == 1


def test_deployed_spa_routes_keep_api_and_assets_separate(tmp_path):
    (tmp_path / "index.html").write_text("<html>Tandem</html>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("export {}", encoding="utf-8")
    app = create_app(Settings(jwt_secret="x" * 32, frontend_dist=tmp_path))
    with TestClient(app) as client:
        assert client.get("/community/banknotes").text == "<html>Tandem</html>"
        assert client.head("/simulator").status_code == 200
        assert client.get("/assets/app.js").text == "export {}"
        assert client.get("/assets/missing.js").status_code == 404
        assert client.get("/api/missing").status_code == 404
        assert client.get("/api/health").json() == {"status": "ok"}


def test_demo_workflow_crosses_all_product_sections(client):
    author = create_member(client, "demo_author")
    guest = create_member(client, "demo_guest")
    assert client.post("/api/banking/demo", headers=author).status_code == 204
    savings = client.get("/api/banking/dashboard", headers=author).json()["savings_balance_minor"]
    goal = client.post("/api/goals", headers=author, json={
        "name": "Vacation", "target_minor": 150_000, "monthly_minor": 25_000,
    }).json()
    assert client.put(f"/api/goals/{goal['id']}/allocation", headers=author, json={
        "allocated_minor": savings,
    }).status_code == 200
    assert client.post(f"/api/goals/{goal['id']}/projection", headers=author, json={
        "amount_minor": 5000, "funding": "contributions",
    }).json()["delay_days"] == 30
    report = client.get("/api/money-leaks", headers=author).json()
    assert report["recurring"] and report["duplicates"]

    post = client.post("/api/community/posts", headers=author, json={
        "post_type": "achievement", "content": "I set a savings goal.", "request_id": str(uuid4()),
    }).json()
    assert client.put(f"/api/community/posts/{post['id']}/like", headers=guest, json={"liked": True}).status_code == 200
    assert client.get("/api/community/posts", headers=author).json()["items"][0]["like_count"] == 1
    assert client.get("/api/goals", headers=guest).json()["goals"] == []

    note = {"currency": "CAD", "denomination": 20, "serial_number": "DEMO6001"}
    assert client.post("/api/banknotes/register", headers=author, json=note).status_code == 200
    assert client.post("/api/banknotes/events", headers=author, json={
        "note": note, "event": {"request_id": str(uuid4()), "city": "Laval", "message": "Happy saving!", "is_hidden": True},
    }).status_code == 201
    assert client.post("/api/banknotes/lookup", headers=guest, json=note).json()["events"][0]["message"] == "Happy saving!"
    assert client.get("/api/deals", headers=guest).json()
