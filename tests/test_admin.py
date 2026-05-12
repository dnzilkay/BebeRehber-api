"""Modül 8: Admin paneli endpoint testleri."""

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
    return user


# ---------------------------- gating ------------------------------------


def test_non_admin_blocked(client):
    h, _ = auth_headers(client)
    for path in ["/admin/users", "/admin/stats"]:
        res = client.get(path, headers=h)
        assert res.status_code == 403, path


def test_premium_user_still_blocked(client, db_session):
    h, email = auth_headers(client)
    user = db_session.query(User).filter_by(email=email).first()
    user.plan = UserPlan.PREMIUM
    db_session.commit()
    res = client.get("/admin/users", headers=h)
    assert res.status_code == 403


# ----------------------------- users ------------------------------------


def test_admin_can_list_users_with_baby_count(client, db_session):
    a_h, a_email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, a_email)
    u_h, u_email = auth_headers(client, email="parent@t.com")
    # parent bir bebek yaratsın
    client.post(
        "/babies",
        headers=u_h,
        json={"name": "Ela", "birth_date": "2026-02-14"},
    )

    res = client.get("/admin/users", headers=a_h)
    assert res.status_code == 200
    rows = {r["email"]: r for r in res.json()}
    assert rows["parent@t.com"]["baby_count"] == 1
    assert rows["adm@t.com"]["role"] == "admin"


def test_admin_user_search(client, db_session):
    a_h, a_email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, a_email)
    auth_headers(client, email="alice@example.com")
    auth_headers(client, email="bob@example.com")

    res = client.get("/admin/users?q=alice", headers=a_h)
    emails = [r["email"] for r in res.json()]
    assert emails == ["alice@example.com"]


def test_admin_user_plan_filter(client, db_session):
    a_h, a_email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, a_email)
    _, premium_email = auth_headers(client, email="prem@t.com")
    auth_headers(client, email="free@t.com")
    user = db_session.query(User).filter_by(email=premium_email).first()
    user.plan = UserPlan.PREMIUM
    db_session.commit()

    res = client.get("/admin/users?plan=premium", headers=a_h)
    emails = [r["email"] for r in res.json()]
    # admin de premium olduğu için listede
    assert "prem@t.com" in emails
    assert "adm@t.com" in emails
    assert "free@t.com" not in emails


# ---------------------------- update -----------------------------------


def test_admin_upgrade_user_to_premium(client, db_session):
    a_h, a_email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, a_email)
    _, u_email = auth_headers(client, email="u@t.com")
    user = db_session.query(User).filter_by(email=u_email).first()

    res = client.patch(
        f"/admin/users/{user.id}",
        headers=a_h,
        json={"plan": "premium"},
    )
    assert res.status_code == 200
    assert res.json()["plan"] == "premium"


def test_admin_suspend_user(client, db_session):
    a_h, a_email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, a_email)
    _, u_email = auth_headers(client, email="u@t.com")
    user = db_session.query(User).filter_by(email=u_email).first()

    res = client.patch(
        f"/admin/users/{user.id}",
        headers=a_h,
        json={"is_active": False},
    )
    assert res.status_code == 200
    assert res.json()["is_active"] is False


def test_admin_cannot_demote_self(client, db_session):
    a_h, a_email = auth_headers(client, email="adm@t.com")
    admin = make_admin(db_session, a_email)
    res = client.patch(
        f"/admin/users/{admin.id}",
        headers=a_h,
        json={"role": "user"},
    )
    assert res.status_code == 400


def test_admin_update_missing_user_404(client, db_session):
    a_h, a_email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, a_email)
    res = client.patch("/admin/users/99999", headers=a_h, json={"plan": "premium"})
    assert res.status_code == 404


# ----------------------------- delete ----------------------------------


def test_admin_delete_user_cascades(client, db_session):
    a_h, a_email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, a_email)
    u_h, u_email = auth_headers(client, email="u@t.com")
    client.post(
        "/babies",
        headers=u_h,
        json={"name": "Ela", "birth_date": "2026-02-14"},
    )
    user = db_session.query(User).filter_by(email=u_email).first()

    res = client.delete(f"/admin/users/{user.id}", headers=a_h)
    assert res.status_code == 204
    # User gerçekten silindi mi
    assert db_session.query(User).filter_by(email=u_email).first() is None


def test_admin_cannot_delete_self(client, db_session):
    a_h, a_email = auth_headers(client, email="adm@t.com")
    admin = make_admin(db_session, a_email)
    res = client.delete(f"/admin/users/{admin.id}", headers=a_h)
    assert res.status_code == 400


# ----------------------------- stats -----------------------------------


def test_admin_stats(client, db_session):
    a_h, a_email = auth_headers(client, email="adm@t.com")
    make_admin(db_session, a_email)
    u_h, u_email = auth_headers(client, email="u@t.com")
    user = db_session.query(User).filter_by(email=u_email).first()
    user.plan = UserPlan.PREMIUM
    db_session.commit()
    client.post(
        "/babies",
        headers=u_h,
        json={"name": "Ela", "birth_date": "2026-02-14"},
    )
    client.post(
        "/community/posts",
        headers=u_h,
        json={"title": "x", "body": "y", "category": "general"},
    )

    res = client.get("/admin/stats", headers=a_h)
    assert res.status_code == 200
    s = res.json()
    assert s["total_users"] == 2
    assert s["premium_users"] == 2  # admin + u
    assert s["admin_users"] == 1
    assert s["total_babies"] == 1
    assert s["total_community_posts"] == 1
