def register_user(client, email="test@example.com", password="StrongPass1", name="Test"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": name},
    )


def test_register_creates_user(client):
    response = register_user(client)

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0
    assert body["user"]["email"] == "test@example.com"
    assert body["user"]["plan"] == "free"
    assert body["user"]["role"] == "user"


def test_register_rejects_duplicate_email(client):
    register_user(client)
    response = register_user(client)

    assert response.status_code == 409
    assert "kayıtlı" in response.json()["detail"]


def test_register_validates_password_length(client):
    response = client.post(
        "/auth/register",
        json={"email": "x@example.com", "password": "short", "name": "X"},
    )
    assert response.status_code == 422


def test_login_with_valid_credentials(client):
    register_user(client)

    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "StrongPass1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "test@example.com"


def test_login_with_wrong_password(client):
    register_user(client)

    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "WrongPass1"},
    )
    assert response.status_code == 401


def test_login_with_unknown_email(client):
    response = client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "AnyPass123"},
    )
    assert response.status_code == 401


def test_me_requires_authentication(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_returns_authenticated_user(client):
    registration = register_user(client).json()
    token = registration["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "test@example.com"
    assert body["name"] == "Test"


def test_me_rejects_invalid_token(client):
    response = client.get(
        "/auth/me", headers={"Authorization": "Bearer not.a.real.token"}
    )
    assert response.status_code == 401


def test_email_is_lowercased_on_register(client):
    response = register_user(client, email="MIXED@Example.com")
    assert response.status_code == 201
    assert response.json()["user"]["email"] == "mixed@example.com"

    login = client.post(
        "/auth/login",
        json={"email": "mixed@example.com", "password": "StrongPass1"},
    )
    assert login.status_code == 200
