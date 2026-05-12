"""Modül 6: Aile paylaşımı (BabyMember + BabyInvite)."""

from datetime import datetime, timedelta, timezone


from app.models.baby_invite import BabyInvite
from app.models.baby_member import BabyMember, BabyMemberRole
from app.models.user import User, UserPlan


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


# -------------------- BabyMember owner backfill -------------------------


def test_create_baby_auto_creates_owner_member(client, db_session):
    h, email = auth_headers(client)
    baby = create_baby(client, h)

    member = db_session.query(BabyMember).filter_by(baby_id=baby["id"]).first()
    assert member is not None
    assert member.role == BabyMemberRole.OWNER


def test_list_babies_shows_owned_and_shared(client, db_session):
    """Co-parent olunca /babies listesinde bebek görünmeli."""
    owner_h, owner_email = auth_headers(client, email="owner@test.com")
    upgrade_to_premium(db_session, owner_email)
    coparent_h, _ = auth_headers(client, email="cp@test.com")

    baby = create_baby(client, owner_h, name="Ada")

    # Davet üret
    invite = client.post(f"/babies/{baby['id']}/invites", headers=owner_h).json()
    # Co-parent kabul eder
    res = client.post(f"/invites/accept/{invite['token']}", headers=coparent_h)
    assert res.status_code == 200

    # Co-parent baby listesinde Ada'yı görür
    listed = client.get("/babies", headers=coparent_h).json()
    names = [b["name"] for b in listed]
    assert "Ada" in names


# ---------------------- Invite create (premium) -------------------------


def test_free_owner_cannot_create_invite(client):
    h, _ = auth_headers(client)
    baby = create_baby(client, h)
    res = client.post(f"/babies/{baby['id']}/invites", headers=h)
    assert res.status_code == 403
    assert "Premium" in res.json()["detail"]


def test_premium_owner_creates_invite_with_url(client, db_session):
    h, email = auth_headers(client)
    upgrade_to_premium(db_session, email)
    baby = create_baby(client, h)
    res = client.post(f"/babies/{baby['id']}/invites", headers=h)
    assert res.status_code == 201
    body = res.json()
    assert body["token"]
    assert "/invite/" in body["url"]
    assert body["url"].endswith(body["token"])


def test_coparent_cannot_create_invite(client, db_session):
    """Co-parent invite oluşturamaz (sadece owner)."""
    owner_h, owner_email = auth_headers(client, email="o@t.com")
    upgrade_to_premium(db_session, owner_email)
    cp_h, cp_email = auth_headers(client, email="cp@t.com")
    upgrade_to_premium(db_session, cp_email)

    baby = create_baby(client, owner_h)
    invite = client.post(f"/babies/{baby['id']}/invites", headers=owner_h).json()
    client.post(f"/invites/accept/{invite['token']}", headers=cp_h)

    # Co-parent invite oluşturmaya çalışır → 403
    res = client.post(f"/babies/{baby['id']}/invites", headers=cp_h)
    assert res.status_code == 403


# ---------------------- Invite accept -----------------------------------


def test_accept_invite_adds_coparent(client, db_session):
    owner_h, owner_email = auth_headers(client, email="o@t.com")
    upgrade_to_premium(db_session, owner_email)
    cp_h, _ = auth_headers(client, email="cp@t.com")

    baby = create_baby(client, owner_h)
    invite = client.post(f"/babies/{baby['id']}/invites", headers=owner_h).json()

    res = client.post(f"/invites/accept/{invite['token']}", headers=cp_h)
    assert res.status_code == 200
    assert res.json()["baby_id"] == baby["id"]

    members = client.get(f"/babies/{baby['id']}/members", headers=owner_h).json()
    assert len(members) == 2
    roles = {m["role"] for m in members}
    assert roles == {"owner", "co_parent"}


def test_accept_invite_idempotent_for_existing_member(client, db_session):
    """Owner kendi davetini kabul etse bile duplicate member oluşmaz."""
    owner_h, owner_email = auth_headers(client, email="o@t.com")
    upgrade_to_premium(db_session, owner_email)
    baby = create_baby(client, owner_h)
    invite = client.post(f"/babies/{baby['id']}/invites", headers=owner_h).json()

    # Owner kendi davetini kabul ediyor — duplicate ekleme yapma
    res = client.post(f"/invites/accept/{invite['token']}", headers=owner_h)
    assert res.status_code == 200

    members = client.get(f"/babies/{baby['id']}/members", headers=owner_h).json()
    assert len(members) == 1  # hâlâ tek üye


def test_accept_invite_token_single_use(client, db_session):
    owner_h, owner_email = auth_headers(client, email="o@t.com")
    upgrade_to_premium(db_session, owner_email)
    cp1_h, _ = auth_headers(client, email="cp1@t.com")
    cp2_h, _ = auth_headers(client, email="cp2@t.com")

    baby = create_baby(client, owner_h)
    invite = client.post(f"/babies/{baby['id']}/invites", headers=owner_h).json()

    client.post(f"/invites/accept/{invite['token']}", headers=cp1_h)
    # İkinci kullanım → 410
    res = client.post(f"/invites/accept/{invite['token']}", headers=cp2_h)
    assert res.status_code == 410


def test_accept_invite_expired(client, db_session):
    owner_h, owner_email = auth_headers(client, email="o@t.com")
    upgrade_to_premium(db_session, owner_email)
    cp_h, _ = auth_headers(client, email="cp@t.com")

    baby = create_baby(client, owner_h)
    invite_res = client.post(f"/babies/{baby['id']}/invites", headers=owner_h).json()

    # Manuel olarak süreyi geçmişe çek
    inv = db_session.query(BabyInvite).filter_by(token=invite_res["token"]).first()
    inv.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    res = client.post(f"/invites/accept/{invite_res['token']}", headers=cp_h)
    assert res.status_code == 410


def test_accept_invite_bad_token(client):
    h, _ = auth_headers(client)
    res = client.post("/invites/accept/does-not-exist", headers=h)
    assert res.status_code == 404


# -------------------- Co-parent erişim --------------------------------


def test_coparent_can_access_baby_resources(client, db_session):
    owner_h, owner_email = auth_headers(client, email="o@t.com")
    upgrade_to_premium(db_session, owner_email)
    cp_h, _ = auth_headers(client, email="cp@t.com")

    baby = create_baby(client, owner_h)
    invite = client.post(f"/babies/{baby['id']}/invites", headers=owner_h).json()
    client.post(f"/invites/accept/{invite['token']}", headers=cp_h)

    # Co-parent care-log ekleyebilir
    res = client.post(
        f"/babies/{baby['id']}/care-logs",
        headers=cp_h,
        json={
            "kind": "feeding",
            "started_at": "2026-05-01T10:00:00Z",
            "amount_ml": 120,
        },
    )
    assert res.status_code == 201

    # Co-parent milestone ekleyebilir
    res = client.post(
        f"/babies/{baby['id']}/milestones",
        headers=cp_h,
        json={"title": "İlk gülümseme", "reached_on": "2026-05-01"},
    )
    assert res.status_code == 201

    # Co-parent günlük entry ekleyebilir
    res = client.post(
        f"/babies/{baby['id']}/entries",
        headers=cp_h,
        json={"title": "Anı", "occurred_on": "2026-05-01"},
    )
    assert res.status_code == 201


# -------------------- Member remove (owner only) ----------------------


def test_owner_can_remove_coparent(client, db_session):
    owner_h, owner_email = auth_headers(client, email="o@t.com")
    upgrade_to_premium(db_session, owner_email)
    cp_h, cp_email = auth_headers(client, email="cp@t.com")

    baby = create_baby(client, owner_h)
    invite = client.post(f"/babies/{baby['id']}/invites", headers=owner_h).json()
    client.post(f"/invites/accept/{invite['token']}", headers=cp_h)

    cp_user = db_session.query(User).filter_by(email=cp_email).first()

    res = client.delete(f"/babies/{baby['id']}/members/{cp_user.id}", headers=owner_h)
    assert res.status_code == 204

    # Co-parent artık erişemez
    listed = client.get("/babies", headers=cp_h).json()
    assert listed == []


def test_owner_cannot_remove_themself(client, db_session):
    owner_h, owner_email = auth_headers(client, email="o@t.com")
    upgrade_to_premium(db_session, owner_email)
    baby = create_baby(client, owner_h)

    owner_user = db_session.query(User).filter_by(email=owner_email).first()
    res = client.delete(
        f"/babies/{baby['id']}/members/{owner_user.id}", headers=owner_h
    )
    assert res.status_code == 400


def test_coparent_cannot_remove_member(client, db_session):
    owner_h, owner_email = auth_headers(client, email="o@t.com")
    upgrade_to_premium(db_session, owner_email)
    cp1_h, cp1_email = auth_headers(client, email="cp1@t.com")
    cp2_h, _ = auth_headers(client, email="cp2@t.com")

    baby = create_baby(client, owner_h)
    # iki ayrı davet (each single-use)
    inv1 = client.post(f"/babies/{baby['id']}/invites", headers=owner_h).json()
    client.post(f"/invites/accept/{inv1['token']}", headers=cp1_h)
    inv2 = client.post(f"/babies/{baby['id']}/invites", headers=owner_h).json()
    client.post(f"/invites/accept/{inv2['token']}", headers=cp2_h)

    cp1_user = db_session.query(User).filter_by(email=cp1_email).first()
    # cp2 cp1'i silmeye çalışıyor — owner değil → 403
    res = client.delete(f"/babies/{baby['id']}/members/{cp1_user.id}", headers=cp2_h)
    assert res.status_code == 403


# -------------------- Owner-only baby ops ----------------------


def test_coparent_cannot_delete_baby(client, db_session):
    owner_h, owner_email = auth_headers(client, email="o@t.com")
    upgrade_to_premium(db_session, owner_email)
    cp_h, _ = auth_headers(client, email="cp@t.com")

    baby = create_baby(client, owner_h)
    invite = client.post(f"/babies/{baby['id']}/invites", headers=owner_h).json()
    client.post(f"/invites/accept/{invite['token']}", headers=cp_h)

    res = client.delete(f"/babies/{baby['id']}", headers=cp_h)
    assert res.status_code == 403
