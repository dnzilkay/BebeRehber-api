from datetime import datetime, timedelta, timezone


def auth_headers(client, email="parent@example.com"):
    res = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass1", "name": "Parent"},
    )
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def create_baby(client, headers, name="Ela"):
    res = client.post(
        "/babies",
        headers=headers,
        json={"name": name, "birth_date": "2026-02-14"},
    )
    return res.json()


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def test_create_sleep_log(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    started = datetime(2026, 5, 4, 21, 0, tzinfo=timezone.utc)
    ended = started + timedelta(hours=2, minutes=30)

    res = client.post(
        f"/babies/{baby['id']}/care-logs",
        headers=h,
        json={
            "kind": "sleep",
            "started_at": _iso(started),
            "ended_at": _iso(ended),
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["kind"] == "sleep"
    assert body["amount_ml"] is None


def test_sleep_requires_ended_at(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    res = client.post(
        f"/babies/{baby['id']}/care-logs",
        headers=h,
        json={
            "kind": "sleep",
            "started_at": _iso(datetime.now(timezone.utc)),
        },
    )
    assert res.status_code == 422


def test_create_feeding_log(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    res = client.post(
        f"/babies/{baby['id']}/care-logs",
        headers=h,
        json={
            "kind": "feeding",
            "started_at": _iso(datetime.now(timezone.utc)),
            "amount_ml": 120,
        },
    )
    assert res.status_code == 201
    assert res.json()["amount_ml"] == 120


def test_diaper_requires_type(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    res = client.post(
        f"/babies/{baby['id']}/care-logs",
        headers=h,
        json={
            "kind": "diaper",
            "started_at": _iso(datetime.now(timezone.utc)),
        },
    )
    assert res.status_code == 422


def test_create_diaper_log(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    res = client.post(
        f"/babies/{baby['id']}/care-logs",
        headers=h,
        json={
            "kind": "diaper",
            "started_at": _iso(datetime.now(timezone.utc)),
            "diaper_type": "pee",
        },
    )
    assert res.status_code == 201
    assert res.json()["diaper_type"] == "pee"


def test_other_user_cannot_create_log(client):
    a = auth_headers(client, email="a@example.com")
    b = auth_headers(client, email="b@example.com")
    baby = create_baby(client, a)

    res = client.post(
        f"/babies/{baby['id']}/care-logs",
        headers=b,
        json={
            "kind": "feeding",
            "started_at": _iso(datetime.now(timezone.utc)),
            "amount_ml": 60,
        },
    )
    assert res.status_code == 404


def test_list_filters_by_kind(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    now = datetime.now(timezone.utc)
    client.post(
        f"/babies/{baby['id']}/care-logs",
        headers=h,
        json={"kind": "feeding", "started_at": _iso(now), "amount_ml": 100},
    )
    client.post(
        f"/babies/{baby['id']}/care-logs",
        headers=h,
        json={
            "kind": "sleep",
            "started_at": _iso(now - timedelta(hours=2)),
            "ended_at": _iso(now - timedelta(hours=1)),
        },
    )

    feeds = client.get(
        f"/babies/{baby['id']}/care-logs?kind=feeding", headers=h
    ).json()
    assert len(feeds) == 1
    assert feeds[0]["kind"] == "feeding"

    sleeps = client.get(
        f"/babies/{baby['id']}/care-logs?kind=sleep", headers=h
    ).json()
    assert len(sleeps) == 1


def test_summary_aggregates(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    now = datetime.now(timezone.utc)

    client.post(
        f"/babies/{baby['id']}/care-logs",
        headers=h,
        json={
            "kind": "sleep",
            "started_at": _iso(now - timedelta(hours=3)),
            "ended_at": _iso(now - timedelta(hours=1)),
        },
    )
    client.post(
        f"/babies/{baby['id']}/care-logs",
        headers=h,
        json={"kind": "feeding", "started_at": _iso(now), "amount_ml": 120},
    )
    client.post(
        f"/babies/{baby['id']}/care-logs",
        headers=h,
        json={
            "kind": "feeding",
            "started_at": _iso(now - timedelta(hours=4)),
            "amount_ml": 80,
        },
    )
    client.post(
        f"/babies/{baby['id']}/care-logs",
        headers=h,
        json={
            "kind": "diaper",
            "started_at": _iso(now),
            "diaper_type": "both",
        },
    )

    res = client.get(f"/babies/{baby['id']}/care-logs/summary", headers=h)
    assert res.status_code == 200
    body = res.json()
    assert body["sleep_minutes"] == 120
    assert body["feeding_count"] == 2
    assert body["feeding_total_ml"] == 200
    assert body["diaper_count"] == 1


def test_delete_log(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    created = client.post(
        f"/babies/{baby['id']}/care-logs",
        headers=h,
        json={
            "kind": "feeding",
            "started_at": _iso(datetime.now(timezone.utc)),
            "amount_ml": 60,
        },
    ).json()

    res = client.delete(
        f"/babies/{baby['id']}/care-logs/{created['id']}", headers=h
    )
    assert res.status_code == 204
