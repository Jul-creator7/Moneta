from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from sqlalchemy import func, select

from app.models import Banknote


NOTE = {"currency": "CAD", "denomination": 20, "serial_number": "ABC123456", "series": "2012 POLYMER"}
LOOKUP = "/api/banknotes/lookup"
REGISTER = "/api/banknotes/register"
EVENTS = "/api/banknotes/events"


def authenticate(client, username):
    credentials = {"email": f"{username}@example.com", "password": "safe-password"}
    assert client.post("/api/auth/register", json={**credentials, "username": username}).status_code == 201
    token = client.post("/api/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def add_event(client, headers, identity, city, message, hidden=False):
    return client.post(EVENTS, headers=headers, json={
        "note": identity,
        "event": {"request_id": str(uuid4()), "city": city, "message": message, "is_hidden": hidden},
    })


def test_lookup_uses_complete_identity_and_hidden_story_reaches_next_member(client):
    first = authenticate(client, "first")
    next_holder = authenticate(client, "next_holder")
    assert client.post(LOOKUP, json=NOTE).status_code == 401
    assert client.post(LOOKUP, headers=first, json=NOTE).status_code == 404
    variant = {**NOTE, "currency": "cad", "serial_number": "abc-123 456", "series": "2012  polymer"}
    registered = client.post(REGISTER, headers=first, json=variant)
    assert registered.json() == {"note": NOTE, "events": [], "before_id": None}
    assert client.post(REGISTER, headers=next_holder, json=NOTE).json() == registered.json()
    assert add_event(client, first, NOTE, "Montréal", "Received at lunch.").status_code == 201
    assert add_event(client, first, NOTE, "Laval", "Good luck, next holder!", True).status_code == 201
    for different in (
        {**NOTE, "currency": "USD"}, {**NOTE, "denomination": 10}, {**NOTE, "series": ""},
    ):
        assert client.post(LOOKUP, headers=next_holder, json=different).status_code == 404
        assert client.post(REGISTER, headers=next_holder, json=different).json()["events"] == []
    result = client.post(LOOKUP, headers=next_holder, json=NOTE)
    assert result.headers["Cache-Control"] == "no-store"
    events = result.json()["events"]
    assert [(event["city"], event["is_hidden"]) for event in events] == [("Laval", True), ("Montréal", False)]
    assert events[0]["message"] == "Good luck, next holder!"
    assert set(events[0]) == {"id", "city", "message", "is_hidden", "created_at"}
    assert "Good luck, next holder!" not in client.get("/api/community/posts", headers=next_holder).text


def test_registration_race_creates_one_row(client):
    first = authenticate(client, "first")
    second = authenticate(client, "second")
    with ThreadPoolExecutor(max_workers=2) as workers:
        replies = list(workers.map(lambda headers: client.post(REGISTER, headers=headers, json=NOTE), [first, second]))
    assert all(reply.status_code == 200 for reply in replies)
    with client.app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Banknote)) == 1


def test_event_validation_retries_and_pagination(client):
    headers = authenticate(client, "storyteller")
    assert add_event(client, headers, NOTE, "Montréal", "Missing note.").status_code == 404
    assert client.post(REGISTER, headers=headers, json={**NOTE, "serial_number": "!"}).status_code == 422
    assert client.post(REGISTER, headers=headers, json=NOTE).status_code == 200
    assert add_event(client, headers, NOTE, "  ", "No city.").status_code == 422
    data = {"note": NOTE, "event": {
        "request_id": str(uuid4()), "city": "Toronto", "message": "First story.", "is_hidden": False,
    }}
    first = client.post(EVENTS, headers=headers, json=data)
    assert first.status_code == 201
    assert client.post(EVENTS, headers=headers, json=data).json() == first.json()
    data["event"]["message"] = "Different story."
    assert client.post(EVENTS, headers=headers, json=data).status_code == 409
    for index in range(15):
        assert add_event(client, headers, NOTE, "Toronto", f"Followup {index}").status_code == 201
    first_page = client.post(LOOKUP, headers=headers, json=NOTE).json()
    assert len(first_page["events"]) == 15
    older = client.post(f"{LOOKUP}?before_id={first_page['before_id']}", headers=headers, json=NOTE).json()
    assert older["events"] == [first.json()]
    assert older["before_id"] is None


def test_demo_deals_are_available_without_location(client):
    headers = authenticate(client, "finder")
    assert client.get("/api/deals").status_code == 401
    result = client.get("/api/deals", headers=headers)
    assert result.status_code == 200
    deals = result.json()
    assert {item["city"] for item in deals} == {"Montréal", "Laval", "Toronto"}
    assert {item["category"] for item in deals} == {"Food", "Clothing"}
    assert all(0 <= item["sale_minor"] < item["original_minor"] for item in deals)
