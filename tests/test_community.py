"""Modül 7: Topluluk Portalı testleri (Premium-only + admin uzman içeriği)."""

from app.models.user import User, UserPlan, UserRole


def auth_headers(client, email="parent@example.com"):
    res = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass1", "name": "Parent"},
    )
    return {"Authorization": f"Bearer {res.json()['access_token']}"}, email


def upgrade_to_premium(db_session, email):
    user = db_session.query(User).filter_by(email=email).first()
    user.plan = UserPlan.PREMIUM
    db_session.commit()


def make_admin(db_session, email):
    user = db_session.query(User).filter_by(email=email).first()
    user.plan = UserPlan.PREMIUM
    user.role = UserRole.ADMIN
    db_session.commit()


# ---------------------------- gating ------------------------------------


def test_free_user_blocked(client):
    h, _ = auth_headers(client)
    res = client.get("/community/posts", headers=h)
    assert res.status_code == 403
    assert "Premium" in res.json()["detail"]


def test_free_user_cannot_post(client):
    h, _ = auth_headers(client)
    res = client.post(
        "/community/posts",
        headers=h,
        json={"title": "Merhaba", "body": "İlk post", "category": "general"},
    )
    assert res.status_code == 403


# ------------------------- post CRUD ------------------------------------


def test_premium_can_create_post(client, db_session):
    h, email = auth_headers(client)
    upgrade_to_premium(db_session, email)
    res = client.post(
        "/community/posts",
        headers=h,
        json={
            "title": "Uyku düzeni nasıl?",
            "body": "3 aylık bebeğim için tavsiye?",
            "category": "sleep",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "Uyku düzeni nasıl?"
    assert body["category"] == "sleep"
    assert body["is_expert"] is False
    assert body["author"]["name"] == "Parent"
    assert body["comments_count"] == 0


def test_admin_post_is_expert(client, db_session):
    h, email = auth_headers(client, email="admin@test.com")
    make_admin(db_session, email)
    res = client.post(
        "/community/posts",
        headers=h,
        json={
            "title": "Pediatr önerisi",
            "body": "Pratik bilgi.",
            "category": "health",
        },
    )
    assert res.status_code == 201
    assert res.json()["is_expert"] is True


def test_list_posts_filter_and_sort(client, db_session):
    h, email = auth_headers(client)
    upgrade_to_premium(db_session, email)

    a_h, a_email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, a_email)

    client.post(
        "/community/posts",
        headers=h,
        json={"title": "Beslenme sorusu", "body": "x", "category": "feeding"},
    )
    client.post(
        "/community/posts",
        headers=h,
        json={"title": "Uyku problemi", "body": "x", "category": "sleep"},
    )
    client.post(
        "/community/posts",
        headers=a_h,
        json={"title": "Uzman: aşı", "body": "x", "category": "health"},
    )

    # En yeni başta
    all_posts = client.get("/community/posts", headers=h).json()
    titles = [p["title"] for p in all_posts]
    assert titles == ["Uzman: aşı", "Uyku problemi", "Beslenme sorusu"]

    # Kategori filtresi
    sleep_only = client.get("/community/posts?category=sleep", headers=h).json()
    assert [p["title"] for p in sleep_only] == ["Uyku problemi"]

    # Sadece uzman
    expert_only = client.get("/community/posts?expert_only=true", headers=h).json()
    assert all(p["is_expert"] for p in expert_only)
    assert len(expert_only) == 1


def test_get_post_detail_with_comments(client, db_session):
    h, email = auth_headers(client)
    upgrade_to_premium(db_session, email)
    cp_h, cp_email = auth_headers(client, email="cp@t.com")
    upgrade_to_premium(db_session, cp_email)

    post = client.post(
        "/community/posts",
        headers=h,
        json={"title": "p1", "body": "soru", "category": "general"},
    ).json()
    client.post(
        f"/community/posts/{post['id']}/comments",
        headers=cp_h,
        json={"body": "Cevap 1"},
    )
    client.post(
        f"/community/posts/{post['id']}/comments",
        headers=h,
        json={"body": "Cevap 2"},
    )

    detail = client.get(f"/community/posts/{post['id']}", headers=h).json()
    assert detail["comments_count"] == 2
    assert len(detail["comments"]) == 2
    assert detail["comments"][0]["body"] == "Cevap 1"
    assert detail["comments"][1]["body"] == "Cevap 2"


def test_delete_post_owner(client, db_session):
    h, email = auth_headers(client)
    upgrade_to_premium(db_session, email)
    post = client.post(
        "/community/posts",
        headers=h,
        json={"title": "x", "body": "y", "category": "general"},
    ).json()
    res = client.delete(f"/community/posts/{post['id']}", headers=h)
    assert res.status_code == 204


def test_delete_post_other_user_forbidden(client, db_session):
    a_h, a_email = auth_headers(client, email="a@t.com")
    upgrade_to_premium(db_session, a_email)
    b_h, b_email = auth_headers(client, email="b@t.com")
    upgrade_to_premium(db_session, b_email)

    post = client.post(
        "/community/posts",
        headers=a_h,
        json={"title": "x", "body": "y", "category": "general"},
    ).json()
    res = client.delete(f"/community/posts/{post['id']}", headers=b_h)
    assert res.status_code == 403


def test_admin_can_delete_any_post(client, db_session):
    h, email = auth_headers(client)
    upgrade_to_premium(db_session, email)
    a_h, a_email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, a_email)

    post = client.post(
        "/community/posts",
        headers=h,
        json={"title": "x", "body": "y", "category": "general"},
    ).json()
    res = client.delete(f"/community/posts/{post['id']}", headers=a_h)
    assert res.status_code == 204


# ---------------------------- comments ----------------------------------


def test_create_comment_premium(client, db_session):
    h, email = auth_headers(client)
    upgrade_to_premium(db_session, email)
    post = client.post(
        "/community/posts",
        headers=h,
        json={"title": "x", "body": "y", "category": "general"},
    ).json()
    res = client.post(
        f"/community/posts/{post['id']}/comments",
        headers=h,
        json={"body": "merhaba"},
    )
    assert res.status_code == 201
    assert res.json()["body"] == "merhaba"


def test_create_comment_on_missing_post_404(client, db_session):
    h, email = auth_headers(client)
    upgrade_to_premium(db_session, email)
    res = client.post(
        "/community/posts/9999/comments",
        headers=h,
        json={"body": "x"},
    )
    assert res.status_code == 404


def test_delete_comment_owner(client, db_session):
    h, email = auth_headers(client)
    upgrade_to_premium(db_session, email)
    post = client.post(
        "/community/posts",
        headers=h,
        json={"title": "x", "body": "y", "category": "general"},
    ).json()
    comment = client.post(
        f"/community/posts/{post['id']}/comments",
        headers=h,
        json={"body": "x"},
    ).json()
    res = client.delete(f"/community/comments/{comment['id']}", headers=h)
    assert res.status_code == 204


def test_delete_comment_other_user_forbidden(client, db_session):
    a_h, a_email = auth_headers(client, email="a@t.com")
    upgrade_to_premium(db_session, a_email)
    b_h, b_email = auth_headers(client, email="b@t.com")
    upgrade_to_premium(db_session, b_email)

    post = client.post(
        "/community/posts",
        headers=a_h,
        json={"title": "x", "body": "y", "category": "general"},
    ).json()
    comment = client.post(
        f"/community/posts/{post['id']}/comments",
        headers=a_h,
        json={"body": "x"},
    ).json()
    res = client.delete(f"/community/comments/{comment['id']}", headers=b_h)
    assert res.status_code == 403


def test_admin_can_delete_any_comment(client, db_session):
    h, email = auth_headers(client)
    upgrade_to_premium(db_session, email)
    a_h, a_email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, a_email)

    post = client.post(
        "/community/posts",
        headers=h,
        json={"title": "x", "body": "y", "category": "general"},
    ).json()
    comment = client.post(
        f"/community/posts/{post['id']}/comments",
        headers=h,
        json={"body": "x"},
    ).json()
    res = client.delete(f"/community/comments/{comment['id']}", headers=a_h)
    assert res.status_code == 204


def test_deleting_post_cascades_comments(client, db_session):
    h, email = auth_headers(client)
    upgrade_to_premium(db_session, email)
    post = client.post(
        "/community/posts",
        headers=h,
        json={"title": "x", "body": "y", "category": "general"},
    ).json()
    client.post(
        f"/community/posts/{post['id']}/comments",
        headers=h,
        json={"body": "x"},
    )
    client.delete(f"/community/posts/{post['id']}", headers=h)

    from app.models.community_comment import CommunityComment

    remaining = db_session.query(CommunityComment).filter_by(post_id=post["id"]).all()
    assert remaining == []
