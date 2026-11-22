from base64 import b64encode
from io import BytesIO
from uuid import uuid4

from PIL import Image

from test_community import authenticate


def attachment():
    buffer = BytesIO()
    Image.new("RGB", (16, 16), "green").save(buffer, format="PNG")
    return "data:image/png;base64," + b64encode(buffer.getvalue()).decode()


def test_community_supports_image_only_and_captioned_achievement(client):
    author = authenticate(client, "author")
    reader = authenticate(client, "reader")
    path = "/api/community/posts"
    for kind, caption in (("discussion", ""), ("achievement", "Halfway to Madagascar!")):
        payload = {"request_id": str(uuid4()), "post_type": kind, "content": caption, "image": attachment()}
        response = client.post(path, headers=author, json=payload)
        assert response.status_code == 201
        post = response.json()
        assert post["content"] == caption
        assert post["image"].startswith("data:image/webp;base64,")
        assert client.post(path, headers=author, json=payload).json()["id"] == post["id"]
        assert client.get(path, headers=reader).json()["items"][0] == post
    for invalid in (None, "data:image/svg+xml;base64,PHN2Zz4=", "data:image/png;base64,SGVsbG8="):
        assert client.post(path, headers=author, json={
            "request_id": str(uuid4()), "post_type": "discussion", "image": invalid,
        }).status_code == 422


def test_hidden_banknote_image_requires_matching_note_lookup(client):
    author = authenticate(client, "author")
    reader = authenticate(client, "reader")
    note = {"currency": "CAD", "denomination": 20, "serial_number": "IMAGE20"}
    assert client.post("/api/banknotes/register", headers=author, json=note).status_code == 200
    event = {"request_id": str(uuid4()), "city": "Montréal", "is_hidden": True}
    assert client.post("/api/banknotes/events", headers=author, json={"note": note, "event": event}).status_code == 422
    event["image"] = attachment()
    saved = client.post("/api/banknotes/events", headers=author, json={"note": note, "event": event})
    assert saved.status_code == 201
    assert saved.json()["message"] == ""
    assert saved.json()["image"].startswith("data:image/webp;base64,")
    lookup = "/api/banknotes/lookup"
    assert client.post(lookup, json=note).status_code == 401
    assert client.post(lookup, headers=reader, json={**note, "denomination": 10}).status_code == 404
    assert client.post(lookup, headers=reader, json=note).json()["events"] == [saved.json()]
