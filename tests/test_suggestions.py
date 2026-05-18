"""BACKLOG #3: Premium-only kişiselleştirilmiş öneriler endpoint'i."""

from datetime import date, datetime, timedelta, timezone

from app.models.user import User, UserPlan


def _register(client, email="parent@example.com"):
    res = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass1", "name": "P"},
    )
    return {"Authorization": f"Bearer {res.json()['access_token']}"}, email


def _upgrade(db_session, email):
    user = db_session.query(User).filter_by(email=email).first()
    user.plan = UserPlan.PREMIUM
    db_session.commit()


def _baby(client, h, birth_date="2026-02-14"):
    return client.post(
        "/babies",
        headers=h,
        json={"name": "Ela", "birth_date": birth_date},
    ).json()


def test_suggestions_free_user_blocked(client):
    h, _ = _register(client)
    baby = _baby(client, h)
    res = client.get(f"/babies/{baby['id']}/suggestions", headers=h)
    assert res.status_code == 403
    assert "Premium" in res.json()["detail"]


def test_suggestions_premium_returns_list(client, db_session):
    h, email = _register(client)
    _upgrade(db_session, email)
    # 6 ay önce doğan bebek → ek gıda dönemi tip'i gelmeli
    six_months_ago = (date.today() - timedelta(days=180)).isoformat()
    baby = _baby(client, h, birth_date=six_months_ago)

    res = client.get(f"/babies/{baby['id']}/suggestions", headers=h)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Yaş bazlı bir tip her zaman olmalı
    assert any(s["category"] == "tip" for s in data)


def test_suggestions_skip_recorded_milestones(client, db_session):
    h, email = _register(client)
    _upgrade(db_session, email)
    # 9 ay önce doğan → emekleme (8-11 ay) ve "tutunarak ayağa kalkar" (9-13)
    nine_months_ago = (date.today() - timedelta(days=270)).isoformat()
    baby = _baby(client, h, birth_date=nine_months_ago)

    before = client.get(f"/babies/{baby['id']}/suggestions", headers=h).json()
    crawls_ids = [s["id"] for s in before if s["id"] == "milestone_crawls"]
    assert crawls_ids, "9 aylık bebek için emekleme önerisi olmalı"

    # Emekleme milestone'unu kaydet → öneri listesinden düşmeli
    client.post(
        f"/babies/{baby['id']}/milestones",
        headers=h,
        json={
            "title": "Emekledi",
            "preset_id": "crawls",
            "reached_on": date.today().isoformat(),
        },
    )
    after = client.get(f"/babies/{baby['id']}/suggestions", headers=h).json()
    assert not any(s["id"] == "milestone_crawls" for s in after)


def test_suggestions_detect_low_sleep(client, db_session):
    h, email = _register(client)
    _upgrade(db_session, email)
    six_months_ago = (date.today() - timedelta(days=180)).isoformat()
    baby = _baby(client, h, birth_date=six_months_ago)

    # Son 7 gün uyku: günlük sadece 6 saat → 12-15 sa önerisinin altında
    now = datetime.now(timezone.utc)
    for d in range(7):
        start = now - timedelta(days=d, hours=8)
        end = start + timedelta(hours=6)
        client.post(
            f"/babies/{baby['id']}/care-logs",
            headers=h,
            json={
                "kind": "sleep",
                "started_at": start.isoformat(),
                "ended_at": end.isoformat(),
            },
        )

    data = client.get(f"/babies/{baby['id']}/suggestions", headers=h).json()
    assert any(s["id"] == "sleep_low" for s in data)


def test_suggestions_no_logs_returns_logging_tip(client, db_session):
    h, email = _register(client)
    _upgrade(db_session, email)
    baby = _baby(client, h)

    data = client.get(f"/babies/{baby['id']}/suggestions", headers=h).json()
    assert any(s["id"] == "logging_tip" for s in data)
