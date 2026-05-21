def test_register_valid(client):
    res = client.post("/auth/register", json={
        "email": "testuser@example.com",
        "password": "password123"
    })
    assert res.status_code == 201
    assert res.json()["email"] == "testuser@example.com"


def test_register_duplicate_email(client):
    client.post("/auth/register", json={
        "email": "duplicate@example.com",
        "password": "password123"
    })
    res = client.post("/auth/register", json={
        "email": "duplicate@example.com",
        "password": "password123"
    })
    assert res.status_code == 409


def test_register_short_password(client):
    res = client.post("/auth/register", json={
        "email": "short@example.com",
        "password": "abc"
    })
    assert res.status_code == 422


def test_register_invalid_email(client):
    res = client.post("/auth/register", json={
        "email": "notanemail",
        "password": "password123"
    })
    assert res.status_code == 422


def test_login_valid(client):
    client.post("/auth/register", json={
        "email": "loginuser@example.com",
        "password": "password123"
    })
    res = client.post("/auth/login", json={
        "email": "loginuser@example.com",
        "password": "password123"
    })
    assert res.status_code == 200
    assert "token" in res.json()


def test_login_wrong_password(client):
    client.post("/auth/register", json={
        "email": "wrongpass@example.com",
        "password": "password123"
    })
    res = client.post("/auth/login", json={
        "email": "wrongpass@example.com",
        "password": "wrongpassword"
    })
    assert res.status_code == 401


def test_login_nonexistent_email(client):
    res = client.post("/auth/login", json={
        "email": "nobody@example.com",
        "password": "password123"
    })
    assert res.status_code == 401


def test_jwt_contains_fields(client):
    client.post("/auth/register", json={
        "email": "jwtuser@example.com",
        "password": "password123"
    })
    res = client.post("/auth/login", json={
        "email": "jwtuser@example.com",
        "password": "password123"
    })
    assert "token" in res.json()
    from jose import jwt
    payload = jwt.decode(res.json()["token"],key="", options={"verify_signature": False})
    assert "sub" in payload
    assert "exp" in payload
