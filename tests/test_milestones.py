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


def test_create_milestone_with_preset(client):
    h = auth_headers(client)
    baby = create_baby(client, h)

    res = client.post(
        f"/babies/{baby['id']}/milestones",
        headers=h,
        json={
            "preset_id": "first_smile",
            "title": "İlk gülümseme",
            "category": "social",
            "reached_on": "2026-04-10",
            "note": "Sabah uyandığında.",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["preset_id"] == "first_smile"
    assert body["title"] == "İlk gülümseme"
    assert body["category"] == "social"
    assert body["reached_on"] == "2026-04-10"


def test_create_milestone_freeform(client):
    h = auth_headers(client)
    baby = create_baby(client, h)

    res = client.post(
        f"/babies/{baby['id']}/milestones",
        headers=h,
        json={
            "title": "Köpeğe el salladı",
            "reached_on": "2026-05-01",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["preset_id"] is None
    assert body["category"] == "other"


def test_list_milestones_sorted_newest_first(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    client.post(
        f"/babies/{baby['id']}/milestones",
        headers=h,
        json={"title": "Eski", "reached_on": "2026-03-01"},
    )
    client.post(
        f"/babies/{baby['id']}/milestones",
        headers=h,
        json={"title": "Yeni", "reached_on": "2026-05-01"},
    )

    res = client.get(f"/babies/{baby['id']}/milestones", headers=h)
    assert res.status_code == 200
    titles = [m["title"] for m in res.json()]
    assert titles == ["Yeni", "Eski"]


def test_list_milestones_limit(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    for i in range(7):
        client.post(
            f"/babies/{baby['id']}/milestones",
            headers=h,
            json={"title": f"m{i}", "reached_on": f"2026-04-{i + 1:02d}"},
        )

    res = client.get(f"/babies/{baby['id']}/milestones?limit=3", headers=h)
    assert res.status_code == 200
    assert len(res.json()) == 3


def test_list_milestones_filter_by_category(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    client.post(
        f"/babies/{baby['id']}/milestones",
        headers=h,
        json={
            "title": "Yuvarlandı",
            "category": "motor",
            "reached_on": "2026-04-15",
        },
    )
    client.post(
        f"/babies/{baby['id']}/milestones",
        headers=h,
        json={
            "title": "İlk kelime",
            "category": "language",
            "reached_on": "2026-04-20",
        },
    )

    res = client.get(f"/babies/{baby['id']}/milestones?category=motor", headers=h)
    assert res.status_code == 200
    titles = [m["title"] for m in res.json()]
    assert titles == ["Yuvarlandı"]


def test_update_milestone(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    m = client.post(
        f"/babies/{baby['id']}/milestones",
        headers=h,
        json={"title": "Eski başlık", "reached_on": "2026-04-10"},
    ).json()

    res = client.patch(
        f"/babies/{baby['id']}/milestones/{m['id']}",
        headers=h,
        json={"title": "Yeni başlık", "note": "Detay"},
    )
    assert res.status_code == 200
    assert res.json()["title"] == "Yeni başlık"
    assert res.json()["note"] == "Detay"


def test_delete_milestone(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    m = client.post(
        f"/babies/{baby['id']}/milestones",
        headers=h,
        json={"title": "x", "reached_on": "2026-04-10"},
    ).json()

    res = client.delete(f"/babies/{baby['id']}/milestones/{m['id']}", headers=h)
    assert res.status_code == 204

    listed = client.get(f"/babies/{baby['id']}/milestones", headers=h).json()
    assert listed == []


def test_other_user_cannot_access(client):
    a = auth_headers(client, email="a@example.com")
    b = auth_headers(client, email="b@example.com")
    baby = create_baby(client, a)

    res = client.post(
        f"/babies/{baby['id']}/milestones",
        headers=b,
        json={"title": "x", "reached_on": "2026-04-10"},
    )
    assert res.status_code == 404


def test_milestone_404_for_wrong_baby(client):
    h = auth_headers(client)
    baby_a = create_baby(client, h, name="A")
    baby_b = create_baby(client, h, name="B")
    m = client.post(
        f"/babies/{baby_a['id']}/milestones",
        headers=h,
        json={"title": "x", "reached_on": "2026-04-10"},
    ).json()

    # baby_b altında baby_a'nın milestone'unu sorguladığımızda 404
    res = client.patch(
        f"/babies/{baby_b['id']}/milestones/{m['id']}",
        headers=h,
        json={"title": "değişti"},
    )
    assert res.status_code == 404
