"""Modül 9: Sosyal Medya Yönetimi testleri (Admin-only)."""

from app.models.user import User, UserPlan, UserRole


def auth_headers(client, email="user@example.com"):
    res = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass1", "name": "User"},
    )
    return {"Authorization": f"Bearer {res.json()['access_token']}"}, email


def make_admin(db_session, email):
    user = db_session.query(User).filter_by(email=email).first()
    user.plan = UserPlan.PREMIUM
    user.role = UserRole.ADMIN
    db_session.commit()


# ---------------------------- gating ------------------------------------


def test_non_admin_blocked(client, db_session):
    # Free
    h, _ = auth_headers(client)
    for path in ["/admin/social-posts", "/admin/social-posts/stats"]:
        res = client.get(path, headers=h)
        assert res.status_code == 403, path


def test_premium_user_still_blocked(client, db_session):
    h, email = auth_headers(client)
    user = db_session.query(User).filter_by(email=email).first()
    user.plan = UserPlan.PREMIUM
    db_session.commit()
    res = client.get("/admin/social-posts", headers=h)
    assert res.status_code == 403


# ---------------------------- CRUD --------------------------------------


def test_admin_create_post(client, db_session):
    h, email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, email)

    res = client.post(
        "/admin/social-posts",
        headers=h,
        json={
            "platform": "instagram",
            "title": "Lansman duyurusu",
            "body": "BebeRehber yayında!",
            "status": "scheduled",
            "scheduled_for": "2026-06-01T18:00:00Z",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["platform"] == "instagram"
    assert body["status"] == "scheduled"
    assert body["title"] == "Lansman duyurusu"
    assert body["likes"] == 0
    assert body["published_at"] is None


def test_admin_create_published_sets_published_at(client, db_session):
    h, email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, email)
    res = client.post(
        "/admin/social-posts",
        headers=h,
        json={
            "platform": "x",
            "title": "Anlık paylaşım",
            "status": "published",
        },
    )
    assert res.status_code == 201
    assert res.json()["published_at"] is not None


def test_admin_list_with_filter(client, db_session):
    h, email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, email)
    client.post(
        "/admin/social-posts",
        headers=h,
        json={"platform": "instagram", "title": "ig", "status": "draft"},
    )
    client.post(
        "/admin/social-posts",
        headers=h,
        json={"platform": "tiktok", "title": "tt", "status": "scheduled"},
    )

    all_rows = client.get("/admin/social-posts", headers=h).json()
    assert len(all_rows) == 2

    ig_only = client.get("/admin/social-posts?platform=instagram", headers=h).json()
    assert [r["title"] for r in ig_only] == ["ig"]

    drafts = client.get("/admin/social-posts?status=draft", headers=h).json()
    assert [r["title"] for r in drafts] == ["ig"]


def test_admin_update_post(client, db_session):
    h, email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, email)
    post = client.post(
        "/admin/social-posts",
        headers=h,
        json={"platform": "instagram", "title": "x", "status": "draft"},
    ).json()

    res = client.patch(
        f"/admin/social-posts/{post['id']}",
        headers=h,
        json={"status": "published", "likes": 100, "reach": 5000},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "published"
    assert body["likes"] == 100
    assert body["reach"] == 5000
    assert body["published_at"] is not None


def test_admin_delete_post(client, db_session):
    h, email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, email)
    post = client.post(
        "/admin/social-posts",
        headers=h,
        json={"platform": "x", "title": "x", "status": "draft"},
    ).json()

    res = client.delete(f"/admin/social-posts/{post['id']}", headers=h)
    assert res.status_code == 204
    listed = client.get("/admin/social-posts", headers=h).json()
    assert listed == []


def test_admin_update_missing_post_404(client, db_session):
    h, email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, email)
    res = client.patch(
        "/admin/social-posts/9999",
        headers=h,
        json={"status": "published"},
    )
    assert res.status_code == 404


# ----------------------------- stats -----------------------------------


def test_admin_stats(client, db_session):
    h, email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, email)
    # 2 draft + 1 scheduled + 1 published (reach 1000, likes 50, comments 20, shares 10)
    client.post(
        "/admin/social-posts",
        headers=h,
        json={"platform": "instagram", "title": "d1", "status": "draft"},
    )
    client.post(
        "/admin/social-posts",
        headers=h,
        json={"platform": "tiktok", "title": "d2", "status": "draft"},
    )
    client.post(
        "/admin/social-posts",
        headers=h,
        json={"platform": "instagram", "title": "s1", "status": "scheduled"},
    )
    p = client.post(
        "/admin/social-posts",
        headers=h,
        json={"platform": "x", "title": "p1", "status": "published"},
    ).json()
    client.patch(
        f"/admin/social-posts/{p['id']}",
        headers=h,
        json={"likes": 50, "comments_count": 20, "shares": 10, "reach": 1000},
    )

    res = client.get("/admin/social-posts/stats", headers=h).json()
    assert res["total_posts"] == 4
    assert res["drafts"] == 2
    assert res["scheduled"] == 1
    assert res["published"] == 1
    assert res["total_reach"] == 1000
    assert res["total_engagement"] == 80  # 50+20+10
