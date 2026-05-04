from datetime import datetime, timedelta, timezone


def auth_headers(client, email="parent@example.com"):
    res = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass1", "name": "Parent"},
    )
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def create_baby(client, headers, name="Ela"):
    return client.post(
        "/babies",
        headers=headers,
        json={"name": name, "birth_date": "2026-02-14"},
    ).json()


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def test_create_reminder(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    due = datetime.now(timezone.utc) + timedelta(days=14)

    res = client.post(
        f"/babies/{baby['id']}/reminders",
        headers=h,
        json={
            "title": "2 aylık aşıları",
            "kind": "vaccine",
            "due_at": _iso(due),
            "note": "Pediatri randevusu",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "2 aylık aşıları"
    assert body["kind"] == "vaccine"
    assert body["completed_at"] is None


def test_list_reminders_sorted_by_due_at(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    now = datetime.now(timezone.utc)
    client.post(
        f"/babies/{baby['id']}/reminders",
        headers=h,
        json={
            "title": "İkinci",
            "due_at": _iso(now + timedelta(days=10)),
        },
    )
    client.post(
        f"/babies/{baby['id']}/reminders",
        headers=h,
        json={
            "title": "Birinci",
            "due_at": _iso(now + timedelta(days=2)),
        },
    )

    res = client.get(f"/babies/{baby['id']}/reminders", headers=h)
    assert res.status_code == 200
    titles = [r["title"] for r in res.json()]
    assert titles == ["Birinci", "İkinci"]


def test_upcoming_filter_excludes_completed(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    now = datetime.now(timezone.utc)
    r1 = client.post(
        f"/babies/{baby['id']}/reminders",
        headers=h,
        json={"title": "A", "due_at": _iso(now + timedelta(days=2))},
    ).json()
    client.post(
        f"/babies/{baby['id']}/reminders",
        headers=h,
        json={"title": "B", "due_at": _iso(now + timedelta(days=3))},
    )

    # A'yı tamamla
    client.patch(
        f"/babies/{baby['id']}/reminders/{r1['id']}",
        headers=h,
        json={"completed": True},
    )

    upcoming = client.get(
        f"/babies/{baby['id']}/reminders?upcoming=true", headers=h
    ).json()
    titles = [r["title"] for r in upcoming]
    assert titles == ["B"]


def test_complete_and_uncomplete(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    r = client.post(
        f"/babies/{baby['id']}/reminders",
        headers=h,
        json={
            "title": "Doktor",
            "due_at": _iso(datetime.now(timezone.utc) + timedelta(days=7)),
        },
    ).json()

    res = client.patch(
        f"/babies/{baby['id']}/reminders/{r['id']}",
        headers=h,
        json={"completed": True},
    )
    assert res.status_code == 200
    assert res.json()["completed_at"] is not None

    res2 = client.patch(
        f"/babies/{baby['id']}/reminders/{r['id']}",
        headers=h,
        json={"completed": False},
    )
    assert res2.json()["completed_at"] is None


def test_other_user_cannot_access(client):
    a = auth_headers(client, email="a@example.com")
    b = auth_headers(client, email="b@example.com")
    baby = create_baby(client, a)

    res = client.post(
        f"/babies/{baby['id']}/reminders",
        headers=b,
        json={
            "title": "x",
            "due_at": _iso(datetime.now(timezone.utc) + timedelta(days=1)),
        },
    )
    assert res.status_code == 404


def test_delete_reminder(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    r = client.post(
        f"/babies/{baby['id']}/reminders",
        headers=h,
        json={
            "title": "x",
            "due_at": _iso(datetime.now(timezone.utc) + timedelta(days=1)),
        },
    ).json()

    res = client.delete(f"/babies/{baby['id']}/reminders/{r['id']}", headers=h)
    assert res.status_code == 204
