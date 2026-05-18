"""BACKLOG #2: GuideArticle public liste + admin CRUD."""

from app.models.user import User, UserRole


def _register(client, email="parent@example.com"):
    res = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass1", "name": "P"},
    )
    return {"Authorization": f"Bearer {res.json()['access_token']}"}, email


def _make_admin(db_session, email):
    user = db_session.query(User).filter_by(email=email).first()
    user.role = UserRole.ADMIN
    db_session.commit()


def _sample_payload(**overrides):
    base = {
        "title": "Hamilelikte ilk 3 ay",
        "summary": "İlk trimestre temel rehberi: bulantı, yorgunluk, doktor kontrolleri.",
        "body": "Hamileliğin ilk üç ayında vücudun hızla değişir. Çiğ etten uzak dur.",
        "category": "pregnancy",
    }
    base.update(overrides)
    return base


def test_guides_list_empty_when_no_articles(client):
    res = client.get("/guides")
    assert res.status_code == 200
    assert res.json() == []


def test_admin_can_create_guide(client, db_session):
    h, email = _register(client, email="admin@x.com")
    _make_admin(db_session, email)

    res = client.post("/guides", headers=h, json=_sample_payload())
    assert res.status_code == 201, res.json()
    data = res.json()
    assert data["slug"] == "hamilelikte-ilk-3-ay"
    assert data["category"] == "pregnancy"
    assert "body" in data


def test_free_user_cannot_create_guide(client):
    h, _ = _register(client)
    res = client.post("/guides", headers=h, json=_sample_payload())
    assert res.status_code == 403


def test_public_list_returns_summary_without_body(client, db_session):
    h, email = _register(client, email="admin@x.com")
    _make_admin(db_session, email)
    client.post("/guides", headers=h, json=_sample_payload())

    # Auth gerekmiyor
    res = client.get("/guides")
    assert res.status_code == 200
    rows = res.json()
    assert len(rows) == 1
    # Summary varyantında body alanı yok
    assert "body" not in rows[0]
    assert rows[0]["title"] == "Hamilelikte ilk 3 ay"


def test_filter_by_category(client, db_session):
    h, email = _register(client, email="admin@x.com")
    _make_admin(db_session, email)
    client.post("/guides", headers=h, json=_sample_payload(category="pregnancy"))
    client.post(
        "/guides",
        headers=h,
        json=_sample_payload(title="Yenidoğan rehberi", category="newborn"),
    )

    res = client.get("/guides?category=newborn").json()
    assert len(res) == 1
    assert res[0]["category"] == "newborn"


def test_detail_by_slug_public(client, db_session):
    h, email = _register(client, email="admin@x.com")
    _make_admin(db_session, email)
    created = client.post("/guides", headers=h, json=_sample_payload()).json()

    res = client.get(f"/guides/{created['slug']}")
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == created["title"]
    assert data["body"]  # body alanı dolu döndü


def test_detail_404_for_unknown_slug(client):
    res = client.get("/guides/yok-boyle-bir-yazi")
    assert res.status_code == 404


def test_slug_collision_appends_suffix(client, db_session):
    h, email = _register(client, email="admin@x.com")
    _make_admin(db_session, email)

    first = client.post("/guides", headers=h, json=_sample_payload()).json()
    # Aynı başlıkla 2. kez oluştur → slug -2 ile çakışmamalı
    second = client.post("/guides", headers=h, json=_sample_payload()).json()
    assert first["slug"] != second["slug"]
    assert second["slug"].endswith("-2")


def test_admin_can_update_guide(client, db_session):
    h, email = _register(client, email="admin@x.com")
    _make_admin(db_session, email)
    created = client.post("/guides", headers=h, json=_sample_payload()).json()

    res = client.patch(
        f"/guides/{created['id']}",
        headers=h,
        json={
            "summary": "Güncellenmiş özet — yeni ipucu eklendi, daha kapsamlı.",
        },
    )
    assert res.status_code == 200
    assert res.json()["summary"].startswith("Güncellenmiş")


def test_admin_can_delete_guide(client, db_session):
    h, email = _register(client, email="admin@x.com")
    _make_admin(db_session, email)
    created = client.post("/guides", headers=h, json=_sample_payload()).json()

    res = client.delete(f"/guides/{created['id']}", headers=h)
    assert res.status_code == 204

    assert client.get(f"/guides/{created['slug']}").status_code == 404


def test_turkish_chars_in_slug(client, db_session):
    h, email = _register(client, email="admin@x.com")
    _make_admin(db_session, email)
    res = client.post(
        "/guides",
        headers=h,
        json=_sample_payload(title="Bebeğin ilk gülümsemesi — şaşırtıcı an"),
    )
    assert res.status_code == 201
    slug = res.json()["slug"]
    assert "ş" not in slug and "ğ" not in slug
    assert slug.startswith("bebegin-ilk-gulumsemesi")
