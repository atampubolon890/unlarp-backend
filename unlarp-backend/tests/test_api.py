def test_signup_login_and_me(client, make_user):
    headers = make_user("andrew")
    assert client.get("/users/me", headers=headers).json()["username"] == "andrew"

    r = client.post(
        "/auth/login", data={"username": "andrew", "password": "correct-horse-battery"}
    )
    assert r.status_code == 200
    assert r.json()["user"]["username"] == "andrew"

    r = client.post("/auth/login", data={"username": "andrew", "password": "wrong-pass"})
    assert r.status_code == 401
    assert client.get("/users/me").status_code == 401


def test_duplicate_signup_rejected(client, make_user):
    make_user("andrew")
    r = client.post(
        "/auth/signup",
        json={"username": "Andrew", "email": "other@example.com", "password": "x" * 10},
    )
    assert r.status_code == 409


def test_personas_first_is_active_and_switching(client, make_user):
    h = make_user("andrew")
    p1 = client.post(
        "/personas", headers=h, json={"name": "Captain Drew", "occupation": "Firefighter"}
    ).json()
    p2 = client.post(
        "/personas", headers=h, json={"name": "Drew Racer", "occupation": "F1 driver"}
    ).json()
    assert p1["is_active"] is True and p2["is_active"] is False

    r = client.post(f"/personas/{p2['id']}/activate", headers=h)
    assert r.json()["is_active"] is True
    active = [p for p in client.get("/personas", headers=h).json() if p["is_active"]]
    assert [p["id"] for p in active] == [p2["id"]]

    other = make_user("james")
    assert client.post(f"/personas/{p1['id']}/activate", headers=other).status_code == 404


def test_post_requires_selfie(client, make_user):
    h = make_user("andrew", with_selfie=False)
    r = client.post("/posts", headers=h, json={"prompt": "me fighting a fire"})
    assert r.status_code == 400


def test_create_post_uses_active_persona_and_serves_image(client, make_user):
    h = make_user("andrew")
    client.post(
        "/personas", headers=h, json={"name": "Captain Drew", "occupation": "Firefighter"}
    )
    r = client.post(
        "/posts",
        headers=h,
        json={"prompt": "me carrying a cat out of a burning building", "caption": "Tuesday"},
    )
    assert r.status_code == 201, r.text
    post = r.json()
    assert post["persona_occupation"] == "Firefighter"
    assert post["is_ai_generated"] is True

    img = client.get(post["image_url"])
    assert img.status_code == 200
    assert "AI-GENERATED" in img.text


def test_moderation_and_daily_limit(client, make_user):
    h = make_user("andrew")
    assert (
        client.post("/posts", headers=h, json={"prompt": "me naked on a beach"}).status_code
        == 400
    )
    for i in range(3):  # limit is 3 in tests
        assert (
            client.post("/posts", headers=h, json={"prompt": f"me at work {i}"}).status_code
            == 201
        )
    assert client.post("/posts", headers=h, json={"prompt": "one more"}).status_code == 429


def test_follow_feed_likes_comments(client, make_user):
    andrew = make_user("andrew")
    james = make_user("james")
    post = client.post("/posts", headers=andrew, json={"prompt": "me on a podium"}).json()

    # James does not follow Andrew yet: empty home feed, but explore shows it.
    assert client.get("/feed", headers=james).json()["posts"] == []
    assert len(client.get("/feed/explore", headers=james).json()["posts"]) == 1

    assert client.post("/users/andrew/follow", headers=james).status_code == 204
    assert client.post("/users/andrew/follow", headers=james).status_code == 204  # idempotent
    assert client.post("/users/james/follow", headers=james).status_code == 400
    feed = client.get("/feed", headers=james).json()["posts"]
    assert [p["id"] for p in feed] == [post["id"]]

    profile = client.get("/users/andrew", headers=james).json()
    assert profile["follower_count"] == 1 and profile["is_following"] is True
    assert profile["post_count"] == 1

    client.post(f"/posts/{post['id']}/like", headers=james)
    client.post(f"/posts/{post['id']}/like", headers=james)  # no double likes
    c = client.post(
        f"/posts/{post['id']}/comments", headers=james, json={"body": "legend"}
    ).json()
    seen = client.get(f"/posts/{post['id']}", headers=james).json()
    assert seen["like_count"] == 1 and seen["liked_by_me"] is True
    assert seen["comment_count"] == 1
    assert client.get(f"/posts/{post['id']}", headers=andrew).json()["liked_by_me"] is False

    client.delete(f"/posts/{post['id']}/like", headers=james)
    assert client.get(f"/posts/{post['id']}", headers=james).json()["like_count"] == 0

    # Post owner can delete someone else's comment; strangers cannot delete the post.
    assert client.delete(f"/comments/{c['id']}", headers=andrew).status_code == 204
    assert client.delete(f"/posts/{post['id']}", headers=james).status_code == 403
    assert client.delete(f"/posts/{post['id']}", headers=andrew).status_code == 204

    client.delete("/users/andrew/follow", headers=james)
    assert client.get("/users/andrew", headers=james).json()["follower_count"] == 0


def test_feed_pagination(client, make_user):
    h = make_user("andrew")
    ids = [
        client.post("/posts", headers=h, json={"prompt": f"scene {i}"}).json()["id"]
        for i in range(3)
    ]
    page1 = client.get("/feed?limit=2", headers=h).json()
    assert [p["id"] for p in page1["posts"]] == [ids[2], ids[1]]
    page2 = client.get(
        f"/feed?limit=2&before_id={page1['next_before_id']}", headers=h
    ).json()
    assert [p["id"] for p in page2["posts"]] == [ids[0]]
    assert page2["next_before_id"] is None


def test_selfie_rejects_non_images_and_stays_private(client, make_user):
    h = make_user("andrew", with_selfie=False)
    r = client.post(
        "/users/me/selfies", headers=h, files={"file": ("a.txt", b"hi", "text/plain")}
    )
    assert r.status_code == 415
    assert client.get("/media/selfies/1/anything.png").status_code == 404
