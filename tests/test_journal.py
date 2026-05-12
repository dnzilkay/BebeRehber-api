import io

import pytest

from app.core import storage


@pytest.fixture(autouse=True)
def fake_storage(monkeypatch):
    """MinIO çağrılarını test sırasında bellekte taklit eder."""
    uploaded: dict[str, tuple[bytes, str]] = {}

    def fake_upload(key: str, data: bytes, content_type: str) -> None:
        uploaded[key] = (data, content_type)

    def fake_delete(key: str) -> None:
        uploaded.pop(key, None)

    def fake_url(key: str) -> str:
        return f"http://fake-cdn/{key}"

    monkeypatch.setattr(storage, "upload_bytes", fake_upload)
    monkeypatch.setattr(storage, "delete_object", fake_delete)
    monkeypatch.setattr(storage, "public_url", fake_url)
    return uploaded


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


# --- Album ----------------------------------------------------------------


def test_create_album(client):
    h = auth_headers(client)
    baby = create_baby(client, h)

    res = client.post(
        f"/babies/{baby['id']}/albums",
        headers=h,
        json={"name": "İlk yıl"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "İlk yıl"
    assert body["entries_count"] == 0
    assert body["cover_url"] is None


def test_list_albums_includes_entry_count(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    album = client.post(
        f"/babies/{baby['id']}/albums", headers=h, json={"name": "A"}
    ).json()
    # 2 entry oluştur, biri albümlü, biri değil
    client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={
            "title": "x",
            "occurred_on": "2026-04-01",
            "album_id": album["id"],
        },
    )
    client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "y", "occurred_on": "2026-04-02"},
    )

    res = client.get(f"/babies/{baby['id']}/albums", headers=h)
    assert res.status_code == 200
    rows = res.json()
    assert len(rows) == 1
    assert rows[0]["entries_count"] == 1


def test_delete_album_keeps_entries(client):
    """Albüm silinince entry'ler kalır (album_id null'a düşer)."""
    h = auth_headers(client)
    baby = create_baby(client, h)
    album = client.post(
        f"/babies/{baby['id']}/albums", headers=h, json={"name": "A"}
    ).json()
    entry = client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={
            "title": "x",
            "occurred_on": "2026-04-01",
            "album_id": album["id"],
        },
    ).json()

    res = client.delete(f"/babies/{baby['id']}/albums/{album['id']}", headers=h)
    assert res.status_code == 204

    fetched = client.get(f"/babies/{baby['id']}/entries", headers=h).json()
    assert len(fetched) == 1
    assert fetched[0]["id"] == entry["id"]
    assert fetched[0]["album_id"] is None


# --- Journal entry --------------------------------------------------------


def test_create_entry_minimal(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    res = client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "İlk gezme", "occurred_on": "2026-04-15"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "İlk gezme"
    assert body["album_id"] is None
    assert body["media"] == []


def test_create_entry_with_invalid_album_404(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    res = client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "x", "occurred_on": "2026-04-15", "album_id": 999},
    )
    assert res.status_code == 404


def test_list_entries_sorted_by_occurred_on_desc(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "Eski", "occurred_on": "2026-03-01"},
    )
    client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "Yeni", "occurred_on": "2026-05-01"},
    )
    rows = client.get(f"/babies/{baby['id']}/entries", headers=h).json()
    assert [r["title"] for r in rows] == ["Yeni", "Eski"]


def test_other_user_cannot_access_entry(client):
    a = auth_headers(client, email="a@example.com")
    b = auth_headers(client, email="b@example.com")
    baby = create_baby(client, a)
    res = client.post(
        f"/babies/{baby['id']}/entries",
        headers=b,
        json={"title": "x", "occurred_on": "2026-04-15"},
    )
    assert res.status_code == 404


# --- Media upload ---------------------------------------------------------


def _png_bytes() -> bytes:
    """1x1 transparent PNG."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff"
        b"\xff?\x00\x05\xfe\x02\xfe\xa7m;\x16\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_upload_image_media(client, fake_storage):
    h = auth_headers(client)
    baby = create_baby(client, h)
    entry = client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "x", "occurred_on": "2026-04-15"},
    ).json()

    files = {"file": ("pic.png", io.BytesIO(_png_bytes()), "image/png")}
    res = client.post(
        f"/babies/{baby['id']}/entries/{entry['id']}/media",
        headers=h,
        files=files,
    )
    assert res.status_code == 201
    body = res.json()
    assert body["kind"] == "image"
    assert body["content_type"] == "image/png"
    assert body["size_bytes"] > 0
    assert body["url"].startswith("http://fake-cdn/journal/")
    # storage'a yazıldı mı?
    assert len(fake_storage) == 1


def test_upload_rejects_non_media(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    entry = client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "x", "occurred_on": "2026-04-15"},
    ).json()

    files = {"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")}
    res = client.post(
        f"/babies/{baby['id']}/entries/{entry['id']}/media",
        headers=h,
        files=files,
    )
    assert res.status_code == 415


def test_entry_includes_media_in_response(client):
    h = auth_headers(client)
    baby = create_baby(client, h)
    entry = client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "x", "occurred_on": "2026-04-15"},
    ).json()
    files = {"file": ("a.png", io.BytesIO(_png_bytes()), "image/png")}
    client.post(
        f"/babies/{baby['id']}/entries/{entry['id']}/media",
        headers=h,
        files=files,
    )

    rows = client.get(f"/babies/{baby['id']}/entries", headers=h).json()
    assert len(rows[0]["media"]) == 1
    assert rows[0]["media"][0]["kind"] == "image"


def test_delete_media(client, fake_storage):
    h = auth_headers(client)
    baby = create_baby(client, h)
    entry = client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "x", "occurred_on": "2026-04-15"},
    ).json()
    files = {"file": ("a.png", io.BytesIO(_png_bytes()), "image/png")}
    media = client.post(
        f"/babies/{baby['id']}/entries/{entry['id']}/media",
        headers=h,
        files=files,
    ).json()
    assert len(fake_storage) == 1

    res = client.delete(
        f"/babies/{baby['id']}/entries/{entry['id']}/media/{media['id']}",
        headers=h,
    )
    assert res.status_code == 204
    assert len(fake_storage) == 0


def test_deleting_entry_cleans_media_storage(client, fake_storage):
    h = auth_headers(client)
    baby = create_baby(client, h)
    entry = client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "x", "occurred_on": "2026-04-15"},
    ).json()
    files = {"file": ("a.png", io.BytesIO(_png_bytes()), "image/png")}
    client.post(
        f"/babies/{baby['id']}/entries/{entry['id']}/media",
        headers=h,
        files=files,
    )
    assert len(fake_storage) == 1

    client.delete(f"/babies/{baby['id']}/entries/{entry['id']}", headers=h)
    assert len(fake_storage) == 0
