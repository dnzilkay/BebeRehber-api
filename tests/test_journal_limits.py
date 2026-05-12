"""Modül 5 Aşama B: Free/Premium paywall enforcement."""

import io

import pytest

from app.core import storage, video
from app.models.user import User, UserPlan


# ----------------------------- fixtures ---------------------------------


@pytest.fixture(autouse=True)
def fake_storage(monkeypatch):
    uploaded: dict[str, tuple[bytes, str]] = {}

    def fake_upload(key, data, content_type):
        uploaded[key] = (data, content_type)

    def fake_delete(key):
        uploaded.pop(key, None)

    def fake_url(key):
        return f"http://fake-cdn/{key}"

    monkeypatch.setattr(storage, "upload_bytes", fake_upload)
    monkeypatch.setattr(storage, "delete_object", fake_delete)
    monkeypatch.setattr(storage, "public_url", fake_url)
    return uploaded


@pytest.fixture
def mock_video_duration(monkeypatch):
    """Test sırasında ffprobe çağrısını mock'lar; yüklenen video'nun
    saniyesini test başına ayarlamak için bu fixture'ı kullan."""
    state: dict[str, int | None] = {"duration": 10}

    def fake_probe(_data, suffix=""):
        return state["duration"]

    monkeypatch.setattr(video, "probe_duration_seconds", fake_probe)
    return state


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


# ----------------------------- album limit ------------------------------


def test_free_max_3_albums(client):
    h, _ = auth_headers(client)
    baby = create_baby(client, h)
    for i in range(3):
        res = client.post(
            f"/babies/{baby['id']}/albums", headers=h, json={"name": f"A{i}"}
        )
        assert res.status_code == 201
    # 4. başarısız
    res = client.post(f"/babies/{baby['id']}/albums", headers=h, json={"name": "A4"})
    assert res.status_code == 403
    assert "Premium" in res.json()["detail"]


def test_premium_can_create_unlimited_albums(client, db_session):
    h, email = auth_headers(client)
    baby = create_baby(client, h)
    upgrade_to_premium(db_session, email)
    for i in range(7):
        res = client.post(
            f"/babies/{baby['id']}/albums", headers=h, json={"name": f"A{i}"}
        )
        assert res.status_code == 201


# --------------------- albüm-medya limit (Free=30) ----------------------


def test_free_max_30_media_per_album(client):
    h, _ = auth_headers(client)
    baby = create_baby(client, h)
    album = client.post(
        f"/babies/{baby['id']}/albums", headers=h, json={"name": "İlk yıl"}
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

    # 30 medya yükle (limit'e kadar)
    for i in range(30):
        files = {"file": (f"p{i}.png", io.BytesIO(_png_bytes()), "image/png")}
        res = client.post(
            f"/babies/{baby['id']}/entries/{entry['id']}/media",
            headers=h,
            files=files,
        )
        assert res.status_code == 201, f"30 medya içinde {i}. başarısız"

    # 31. başarısız
    files = {"file": ("x.png", io.BytesIO(_png_bytes()), "image/png")}
    res = client.post(
        f"/babies/{baby['id']}/entries/{entry['id']}/media",
        headers=h,
        files=files,
    )
    assert res.status_code == 403
    assert "Premium" in res.json()["detail"]


def test_albumsuz_entry_medya_limitsiz_free(client):
    """Albüme bağlı olmayan girişlerde medya limiti UYGULANMAZ."""
    h, _ = auth_headers(client)
    baby = create_baby(client, h)
    entry = client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "x", "occurred_on": "2026-04-01"},
    ).json()
    # 31 medya yükle, hepsi başarılı olmalı
    for i in range(31):
        files = {"file": (f"p{i}.png", io.BytesIO(_png_bytes()), "image/png")}
        res = client.post(
            f"/babies/{baby['id']}/entries/{entry['id']}/media",
            headers=h,
            files=files,
        )
        assert res.status_code == 201


# ----------------------- video duration limit ---------------------------


def test_free_video_30s_limit_rejects_long(client, mock_video_duration):
    h, _ = auth_headers(client)
    baby = create_baby(client, h)
    entry = client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "x", "occurred_on": "2026-04-01"},
    ).json()

    mock_video_duration["duration"] = 45  # > 30 sn
    files = {"file": ("v.mp4", io.BytesIO(b"fake-video"), "video/mp4")}
    res = client.post(
        f"/babies/{baby['id']}/entries/{entry['id']}/media",
        headers=h,
        files=files,
    )
    assert res.status_code == 413
    assert "30 saniye" in res.json()["detail"]
    assert "Premium" in res.json()["detail"]


def test_free_video_30s_limit_accepts_short(client, mock_video_duration):
    h, _ = auth_headers(client)
    baby = create_baby(client, h)
    entry = client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "x", "occurred_on": "2026-04-01"},
    ).json()

    mock_video_duration["duration"] = 25
    files = {"file": ("v.mp4", io.BytesIO(b"fake-video"), "video/mp4")}
    res = client.post(
        f"/babies/{baby['id']}/entries/{entry['id']}/media",
        headers=h,
        files=files,
    )
    assert res.status_code == 201
    assert res.json()["duration_sec"] == 25


def test_premium_video_180s_limit(client, db_session, mock_video_duration):
    h, email = auth_headers(client)
    upgrade_to_premium(db_session, email)
    baby = create_baby(client, h)
    entry = client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "x", "occurred_on": "2026-04-01"},
    ).json()

    # 120 sn → Premium kabul
    mock_video_duration["duration"] = 120
    files = {"file": ("v.mp4", io.BytesIO(b"fake-video"), "video/mp4")}
    res = client.post(
        f"/babies/{baby['id']}/entries/{entry['id']}/media",
        headers=h,
        files=files,
    )
    assert res.status_code == 201

    # 200 sn → Premium da reddeder
    mock_video_duration["duration"] = 200
    files = {"file": ("v.mp4", io.BytesIO(b"fake-video"), "video/mp4")}
    res = client.post(
        f"/babies/{baby['id']}/entries/{entry['id']}/media",
        headers=h,
        files=files,
    )
    assert res.status_code == 413


def test_video_duration_unknown_rejects_free(client, mock_video_duration):
    """ffprobe parse edemediğinde Free güvenli tarafa çekilir, reddedilir."""
    h, _ = auth_headers(client)
    baby = create_baby(client, h)
    entry = client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "x", "occurred_on": "2026-04-01"},
    ).json()

    mock_video_duration["duration"] = None
    files = {"file": ("v.mp4", io.BytesIO(b"fake-video"), "video/mp4")}
    res = client.post(
        f"/babies/{baby['id']}/entries/{entry['id']}/media",
        headers=h,
        files=files,
    )
    assert res.status_code == 400


def test_video_duration_unknown_accepts_premium(
    client, db_session, mock_video_duration
):
    """Premium'da ffprobe failure tolere edilir; duration NULL kalır."""
    h, email = auth_headers(client)
    upgrade_to_premium(db_session, email)
    baby = create_baby(client, h)
    entry = client.post(
        f"/babies/{baby['id']}/entries",
        headers=h,
        json={"title": "x", "occurred_on": "2026-04-01"},
    ).json()

    mock_video_duration["duration"] = None
    files = {"file": ("v.mp4", io.BytesIO(b"fake-video"), "video/mp4")}
    res = client.post(
        f"/babies/{baby['id']}/entries/{entry['id']}/media",
        headers=h,
        files=files,
    )
    assert res.status_code == 201
    assert res.json()["duration_sec"] is None
