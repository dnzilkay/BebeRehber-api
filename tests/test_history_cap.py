"""BACKLOG #4: Free 14 / Premium 365 gün veri geçmişi cap'i.

Cap, ?days=N query param verildiğinde kuvvetli (Free user 365 gün
isteyemez). Param verilmezse mevcut UI'yı bozmamak için filtre yok.
"""

from datetime import date, datetime, timedelta, timezone

from app.models.user import User, UserPlan


def _register(client, email="parent@example.com"):
    res = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass1", "name": "Parent"},
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


def _upgrade(db_session, email):
    user = db_session.query(User).filter_by(email=email).first()
    user.plan = UserPlan.PREMIUM
    db_session.commit()


def _make_baby(client, h):
    return client.post(
        "/babies",
        headers=h,
        json={"name": "Ela", "birth_date": "2026-02-14"},
    ).json()


# --------------------- care-logs (datetime cutoff) -----------------------


def test_care_logs_days_clamped_for_free_user(client):
    h, _ = _register(client)
    baby = _make_baby(client, h)

    # 5 ve 30 gün önceye birer sleep kaydı ekle
    now = datetime.now(timezone.utc)
    for delta in (5, 30):
        start = now - timedelta(days=delta, hours=1)
        end = now - timedelta(days=delta)
        res = client.post(
            f"/babies/{baby['id']}/care-logs",
            headers=h,
            json={
                "kind": "sleep",
                "started_at": start.isoformat(),
                "ended_at": end.isoformat(),
            },
        )
        assert res.status_code == 201

    # Free user ?days=60 dese bile 14 gün cap → sadece 5 günlük dönmeli
    res = client.get(f"/babies/{baby['id']}/care-logs?days=60", headers=h)
    assert res.status_code == 200
    rows = res.json()
    assert len(rows) == 1


def test_care_logs_days_full_for_premium(client, db_session):
    h, email = _register(client)
    _upgrade(db_session, email)
    baby = _make_baby(client, h)

    now = datetime.now(timezone.utc)
    for delta in (5, 30, 60):
        start = now - timedelta(days=delta, hours=1)
        end = now - timedelta(days=delta)
        client.post(
            f"/babies/{baby['id']}/care-logs",
            headers=h,
            json={
                "kind": "sleep",
                "started_at": start.isoformat(),
                "ended_at": end.isoformat(),
            },
        )

    # Premium ?days=90 → tüm 3 kayıt görünmeli
    res = client.get(f"/babies/{baby['id']}/care-logs?days=90", headers=h)
    assert res.status_code == 200
    assert len(res.json()) == 3


# --------------------- milestones (date cutoff) --------------------------


def test_milestones_days_clamped_for_free_user(client):
    h, _ = _register(client)
    baby = _make_baby(client, h)

    today = date.today()
    for delta in (5, 30):
        client.post(
            f"/babies/{baby['id']}/milestones",
            headers=h,
            json={
                "title": f"M{delta}",
                "reached_on": (today - timedelta(days=delta)).isoformat(),
            },
        )

    # days verilmezse hepsi (geriye uyumlu)
    res = client.get(f"/babies/{baby['id']}/milestones", headers=h).json()
    assert len(res) == 2

    # Free ?days=60 → cap 14 → sadece 5 günlük
    res = client.get(f"/babies/{baby['id']}/milestones?days=60", headers=h).json()
    assert len(res) == 1
    assert res[0]["title"] == "M5"


def test_milestones_days_full_for_premium(client, db_session):
    h, email = _register(client)
    _upgrade(db_session, email)
    baby = _make_baby(client, h)

    today = date.today()
    for delta in (5, 30, 60):
        client.post(
            f"/babies/{baby['id']}/milestones",
            headers=h,
            json={
                "title": f"M{delta}",
                "reached_on": (today - timedelta(days=delta)).isoformat(),
            },
        )

    res = client.get(f"/babies/{baby['id']}/milestones?days=90", headers=h).json()
    assert len(res) == 3


# --------------------- journal entries (date cutoff) ---------------------


def test_journal_entries_days_clamped_for_free_user(client):
    h, _ = _register(client)
    baby = _make_baby(client, h)

    today = date.today()
    for delta in (5, 30):
        client.post(
            f"/babies/{baby['id']}/entries",
            headers=h,
            json={
                "title": f"E{delta}",
                "occurred_on": (today - timedelta(days=delta)).isoformat(),
            },
        )

    # days yoksa hepsi
    res = client.get(f"/babies/{baby['id']}/entries", headers=h).json()
    assert len(res) == 2

    # Free ?days=60 → cap 14
    res = client.get(f"/babies/{baby['id']}/entries?days=60", headers=h).json()
    assert len(res) == 1
    assert res[0]["title"] == "E5"


# --------------------- reminders (datetime cutoff) -----------------------


def test_reminders_days_clamped_for_free_user(client):
    h, _ = _register(client)
    baby = _make_baby(client, h)

    now = datetime.now(timezone.utc)
    for delta in (5, 30):
        # geçmiş tarihli reminder (manuel tarih)
        due = now - timedelta(days=delta)
        client.post(
            f"/babies/{baby['id']}/reminders",
            headers=h,
            json={
                "title": f"R{delta}",
                "kind": "vaccine",
                "due_at": due.isoformat(),
            },
        )

    # ?days=60 Free → cap 14 → sadece R5
    res = client.get(f"/babies/{baby['id']}/reminders?days=60", headers=h).json()
    assert len(res) == 1
    assert res[0]["title"] == "R5"
