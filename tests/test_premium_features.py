"""Aşama C: Premium-only timeline ve bulut yedek (export)."""

import io
import json
import zipfile

import pytest

from app.core import storage
from app.models.user import User, UserPlan


@pytest.fixture(autouse=True)
def fake_storage(monkeypatch):
    objects: dict[str, bytes] = {}

    def fake_upload(key, data, content_type):
        objects[key] = data

    def fake_delete(key):
        objects.pop(key, None)

    def fake_url(key):
        return f"http://fake-cdn/{key}"

    def fake_download(key):
        return objects.get(key, b"")

    monkeypatch.setattr(storage, "upload_bytes", fake_upload)
    monkeypatch.setattr(storage, "delete_object", fake_delete)
    monkeypatch.setattr(storage, "public_url", fake_url)
    monkeypatch.setattr(storage, "download_bytes", fake_download)
    return objects


def auth_headers(client, email="parent@example.com"):
    res = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass1", "name": "Parent"},
    )
    return {"Authorization": f"Bearer {res.json()['access_token']}"}, email


def create_baby(client, headers, name="Ela"):
    return client.post(
        "/babies",
        headers=headers,
        json={"name": name, "birth_date": "2026-02-14"},
    ).json()


def upgrade_to_premium(db_session, email):
    user = db_session.query(User).filter_by(email=email).first()
    user.plan = UserPlan.PREMIUM
    db_session.commit()


def _png_bytes() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff"
        b"\xff?\x00\x05\xfe\x02\xfe\xa7m;\x16\x00\x00\x00\x00IEND\xaeB`\x82"
    )


# --------------------------- Timeline -----------------------------------


def test_timeline_free_user_blocked(client):
    h, _ = auth_headers(client)
    baby = create_baby(client, h)
    res = client.get(f"/babies/{baby['id']}/timeline", headers=h)
    assert res.status_code == 403
    assert "Premium" in res.json()["detail"]


def test_timeline_premium_returns_mixed_items(client, db_session):
    h, email = auth_headers(client)
    baby = create_baby(client, h)
    upgrade_to_premium(db_session, email)

    # Bir entry ve bir milestone yarat
    client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "Sahil günü", "occurred_on": "2026-04-15"},
    )
    client.post(
        f"/babies/{baby['id']}/milestones",
        headers=h,
        json={"title": "İlk gülümseme", "reached_on": "2026-04-10"},
    )

    res = client.get(f"/babies/{baby['id']}/timeline", headers=h)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    # En yeni başta
    assert items[0]["kind"] == "journal_entry"
    assert items[0]["date"] == "2026-04-15"
    assert items[1]["kind"] == "milestone"
    assert items[1]["date"] == "2026-04-10"


def test_timeline_includes_album_names(client, db_session):
    h, email = auth_headers(client)
    baby = create_baby(client, h)
    upgrade_to_premium(db_session, email)

    album = client.post(
        f"/babies/{baby['id']}/albums", headers=h, json={"name": "İlk yıl"}
    ).json()
    client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={
            "title": "x",
            "occurred_on": "2026-04-01",
            "album_id": album["id"],
        },
    )

    res = client.get(f"/babies/{baby['id']}/timeline", headers=h).json()
    assert res[0]["album_name"] == "İlk yıl"


# ------------------------------ Export ----------------------------------


def test_export_free_user_blocked(client):
    h, _ = auth_headers(client)
    baby = create_baby(client, h)
    res = client.get(f"/babies/{baby['id']}/export", headers=h)
    assert res.status_code == 403
    assert "Premium" in res.json()["detail"]


def test_export_premium_returns_zip(client, db_session, fake_storage):
    h, email = auth_headers(client)
    baby = create_baby(client, h)
    upgrade_to_premium(db_session, email)

    # Veri yarat: 1 entry + 1 milestone + 1 medya
    entry = client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "Anı", "occurred_on": "2026-04-15"},
    ).json()
    client.post(
        f"/babies/{baby['id']}/milestones",
        headers=h,
        json={"title": "İlk gülümseme", "reached_on": "2026-04-10"},
    )
    files = {"file": ("p.png", io.BytesIO(_png_bytes()), "image/png")}
    client.post(
        f"/babies/{baby['id']}/entries/{entry['id']}/media",
        headers=h,
        files=files,
    )

    res = client.get(f"/babies/{baby['id']}/export", headers=h)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert "attachment" in res.headers["content-disposition"]

    # ZIP içeriğini doğrula
    zf = zipfile.ZipFile(io.BytesIO(res.content))
    names = zf.namelist()
    assert "manifest.json" in names
    # media/ altında en az bir dosya
    media_files = [n for n in names if n.startswith("media/")]
    assert len(media_files) == 1

    manifest = json.loads(zf.read("manifest.json"))
    assert manifest["baby"]["name"] == "Ela"
    assert len(manifest["journal_entries"]) == 1
    assert len(manifest["milestones"]) == 1
    assert len(manifest["journal_entries"][0]["media"]) == 1


def test_export_other_user_404(client, db_session):
    a_h, a_email = auth_headers(client, email="a@example.com")
    b_h, b_email = auth_headers(client, email="b@example.com")
    baby = create_baby(client, a_h)
    upgrade_to_premium(db_session, b_email)

    # B Premium ama A'nın bebeğine erişemez
    res = client.get(f"/babies/{baby['id']}/export", headers=b_h)
    assert res.status_code == 404
