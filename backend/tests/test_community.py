from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4


def authenticate(client, username):
    credentials = {"email": f"{username}@example.com", "password": "safe-password"}
    assert client.post("/api/auth/register", json={**credentials, "username": username}).status_code == 201
    token = client.post("/api/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def publish(client, headers, content="I reached my savings milestone.", kind="achievement", key=None):
    return client.post("/api/community/posts", headers=headers, json={
        "request_id": key or str(uuid4()), "content": content, "post_type": kind,
    })


def test_profile_uses_public_fields_and_post_types(client):
    author = authenticate(client, "author")
    reader = authenticate(client, "reader")
    assert client.get("/api/community/posts").status_code == 401
    assert client.get("/api/community/profiles/author").status_code == 401
    profile = client.get("/api/community/profiles/AUTHOR", headers=reader)
    assert profile.json() == {"username": "author", "display_name": "author"}
    assert client.get("/api/community/profiles/missing", headers=reader).status_code == 404
    edited = client.put("/api/community/profile", headers=author, json={"display_name": "  Ana Saves "})
    assert edited.json() == {"username": "author", "display_name": "Ana Saves"}

    first = publish(client, author).json()
    second = publish(client, reader, "How do you plan for groceries?", "discussion").json()
    feed = client.get("/api/community/posts?limit=1", headers=reader).json()
    assert [post["id"] for post in feed["items"]] == [second["id"]]
    next_page = client.get(f"/api/community/posts?before_id={feed['before_id']}", headers=reader).json()
    assert next_page["items"] == [first]
    assert first["author"] == {"username": "author", "display_name": "Ana Saves"}
    assert first["post_type"] == "achievement"
    assert second["post_type"] == "discussion"
    assert first["created_at"].endswith("Z")
    filtered = client.get("/api/community/posts?author=author", headers=reader).json()
    assert filtered["items"] == [first]
    assert client.put("/api/community/profile", headers=author, json={"display_name": None}).status_code == 200
    assert client.get("/api/community/posts?author=author", headers=reader).json()["items"][0]["author"]["display_name"] == "author"


def test_likes_are_unique_and_viewer_specific_under_retries(client):
    author = authenticate(client, "author")
    reader = authenticate(client, "reader")
    post_id = publish(client, author).json()["id"]
    path = f"/api/community/posts/{post_id}/like"
    with ThreadPoolExecutor(max_workers=2) as workers:
        responses = list(workers.map(lambda _: client.put(path, headers=reader, json={"liked": True}), range(2)))
    assert all(response.json() == {"liked": True, "like_count": 1} for response in responses)
    author_feed = client.get("/api/community/posts", headers=author).json()["items"][0]
    reader_feed = client.get("/api/community/posts", headers=reader).json()["items"][0]
    assert author_feed["like_count"] == reader_feed["like_count"] == 1
    assert author_feed["liked"] is False
    assert reader_feed["liked"] is True
    assert client.put(path, headers=author, json={"liked": True}).json()["like_count"] == 2
    for _ in range(2):
        assert client.put(path, headers=reader, json={"liked": False}).json() == {"liked": False, "like_count": 1}


def test_comments_and_post_retries_do_not_duplicate_content(client):
    author = authenticate(client, "author")
    reader = authenticate(client, "reader")
    key = str(uuid4())
    post_id = publish(client, author, key=key).json()["id"]
    assert publish(client, author, key=key).json()["id"] == post_id
    assert publish(client, author, content="Different content", key=key).status_code == 409
    assert publish(client, author, content="   ").status_code == 422
    second_post_id = publish(client, author, "Another update", "discussion").json()["id"]
    path = f"/api/community/posts/{post_id}/comments"
    assert client.get(path).status_code == 401
    assert client.get("/api/community/posts/9999/comments", headers=author).status_code == 404
    data = {"request_id": str(uuid4()), "content": "  Great work! "}
    created = client.post(path, headers=reader, json=data)
    assert created.status_code == 201
    assert created.json()["comment"]["content"] == "Great work!"
    assert created.json()["comment"]["author"] == {"username": "reader", "display_name": "reader"}
    assert client.post(path, headers=reader, json=data).json() == created.json()
    assert client.post(f"/api/community/posts/{second_post_id}/comments", headers=reader, json=data).status_code == 409
    assert client.post(path, headers=author, json={"request_id": str(uuid4()), "content": "Thank you!"}).status_code == 201
    first_page = client.get(f"{path}?limit=1", headers=author).json()
    assert first_page["items"][0]["content"] == "Thank you!"
    second_page = client.get(f"{path}?before_id={first_page['before_id']}", headers=author).json()
    assert second_page["items"] == [created.json()["comment"]]
    posts = client.get("/api/community/posts", headers=author).json()["items"]
    assert next(post for post in posts if post["id"] == post_id)["comment_count"] == 2
    assert client.post("/api/banking/reset", headers=author).status_code == 204
    assert len(client.get(path, headers=author).json()["items"]) == 2
