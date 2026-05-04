def auth_headers(client, email="parent@example.com", password="StrongPass1", name="Parent"):
    res = client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": name},
    )
    assert res.status_code == 201
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_list_babies_requires_auth(client):
    res = client.get("/babies")
    assert res.status_code == 401


def test_list_babies_empty(client):
    headers = auth_headers(client)
    res = client.get("/babies", headers=headers)
    assert res.status_code == 200
    assert res.json() == []


def test_create_baby(client):
    headers = auth_headers(client)
    res = client.post(
        "/babies",
        headers=headers,
        json={
            "name": "Ela",
            "birth_date": "2026-02-14",
            "gender": "girl",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "Ela"
    assert body["birth_date"] == "2026-02-14"
    assert body["gender"] == "girl"
    assert body["avatar_url"] is None
    assert "id" in body
    assert "owner_id" in body


def test_create_baby_validates_name(client):
    headers = auth_headers(client)
    res = client.post(
        "/babies",
        headers=headers,
        json={"name": "", "birth_date": "2026-02-14"},
    )
    assert res.status_code == 422


def test_list_babies_returns_only_own(client):
    a = auth_headers(client, email="a@example.com")
    b = auth_headers(client, email="b@example.com")

    client.post(
        "/babies",
        headers=a,
        json={"name": "Ela", "birth_date": "2026-02-14"},
    )
    client.post(
        "/babies",
        headers=b,
        json={"name": "Mira", "birth_date": "2026-03-01"},
    )

    res_a = client.get("/babies", headers=a)
    assert res_a.status_code == 200
    names_a = [item["name"] for item in res_a.json()]
    assert names_a == ["Ela"]

    res_b = client.get("/babies", headers=b)
    names_b = [item["name"] for item in res_b.json()]
    assert names_b == ["Mira"]


def test_get_baby_detail(client):
    headers = auth_headers(client)
    created = client.post(
        "/babies",
        headers=headers,
        json={"name": "Ela", "birth_date": "2026-02-14"},
    ).json()

    res = client.get(f"/babies/{created['id']}", headers=headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Ela"


def test_other_user_cannot_access_baby(client):
    a = auth_headers(client, email="a@example.com")
    b = auth_headers(client, email="b@example.com")
    created = client.post(
        "/babies",
        headers=a,
        json={"name": "Ela", "birth_date": "2026-02-14"},
    ).json()

    res = client.get(f"/babies/{created['id']}", headers=b)
    assert res.status_code == 404


def test_update_baby(client):
    headers = auth_headers(client)
    created = client.post(
        "/babies",
        headers=headers,
        json={"name": "Ela", "birth_date": "2026-02-14"},
    ).json()

    res = client.patch(
        f"/babies/{created['id']}",
        headers=headers,
        json={"name": "Elif", "gender": "girl"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Elif"
    assert body["gender"] == "girl"
    assert body["birth_date"] == "2026-02-14"  # değişmedi


def test_other_user_cannot_update_baby(client):
    a = auth_headers(client, email="a@example.com")
    b = auth_headers(client, email="b@example.com")
    created = client.post(
        "/babies",
        headers=a,
        json={"name": "Ela", "birth_date": "2026-02-14"},
    ).json()

    res = client.patch(
        f"/babies/{created['id']}",
        headers=b,
        json={"name": "Hacker"},
    )
    assert res.status_code == 404


def test_delete_baby(client):
    headers = auth_headers(client)
    created = client.post(
        "/babies",
        headers=headers,
        json={"name": "Ela", "birth_date": "2026-02-14"},
    ).json()

    res = client.delete(f"/babies/{created['id']}", headers=headers)
    assert res.status_code == 204

    res2 = client.get(f"/babies/{created['id']}", headers=headers)
    assert res2.status_code == 404


def test_other_user_cannot_delete_baby(client):
    a = auth_headers(client, email="a@example.com")
    b = auth_headers(client, email="b@example.com")
    created = client.post(
        "/babies",
        headers=a,
        json={"name": "Ela", "birth_date": "2026-02-14"},
    ).json()

    res = client.delete(f"/babies/{created['id']}", headers=b)
    assert res.status_code == 404
