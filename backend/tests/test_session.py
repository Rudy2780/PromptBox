"""Tests for cookie-based sessions: cookie attributes, /auth/me, logout, CSRF."""

from fastapi.testclient import TestClient

from app.main import app

CREDENTIALS = {"email": "sessionuser@example.com", "password": "password123"}
COOKIE = "promptbox_session"
CSRF = {"X-Requested-With": "PromptBox"}


def _set_cookie_header(response) -> str:
    headers = [h for h in response.headers.get_list("set-cookie") if COOKIE in h]
    assert headers, "no session cookie was set"
    return headers[0]


def _register_and_login(client):
    client.post("/auth/register", json=CREDENTIALS)
    return client.post("/auth/login", json=CREDENTIALS)


# ---------------------------------------------------------------------------
# Cookie attributes
# ---------------------------------------------------------------------------


def test_session_cookie_is_httponly(client):
    """httpOnly is the whole point: an XSS bug must not be able to read it."""
    raw = _set_cookie_header(_register_and_login(client))
    assert "httponly" in raw.lower()


def test_session_cookie_is_secure_and_samesite_none(client):
    """SameSite=None is required because the SPA and API are different sites,
    and browsers only accept None together with Secure."""
    raw = _set_cookie_header(_register_and_login(client)).lower()
    assert "secure" in raw
    assert "samesite=none" in raw


def test_login_body_does_not_leak_the_token(client):
    res = _register_and_login(client)
    body = res.json()
    assert "token" not in body
    assert COOKIE not in str(body)


# ---------------------------------------------------------------------------
# Session restoration and logout
# ---------------------------------------------------------------------------


def test_me_returns_the_signed_in_user(client):
    _register_and_login(client)
    res = client.get("/auth/me")
    assert res.status_code == 200
    assert res.json()["email"] == CREDENTIALS["email"]


def test_me_requires_a_session(client):
    assert client.get("/auth/me").status_code == 401


def test_logout_clears_the_cookie_server_side(client):
    _register_and_login(client)
    assert client.get("/auth/me").status_code == 200

    res = client.post("/auth/logout", headers=CSRF)
    assert res.status_code == 200

    # The browser is instructed to drop it, and the session stops working.
    assert not client.cookies.get(COOKIE)
    assert client.get("/auth/me").status_code == 401


def test_logout_works_without_a_valid_session(client):
    """Logging out with an expired or absent session must still clear, not 401."""
    assert client.post("/auth/logout", headers=CSRF).status_code == 200


def test_session_survives_a_new_request_without_javascript_state(client):
    """The cookie alone re-authenticates -- this is what fixes refresh-logout."""
    _register_and_login(client)
    fresh = TestClient(app, base_url="https://testserver")
    fresh.cookies.set(COOKIE, client.cookies.get(COOKIE))
    assert fresh.get("/auth/me").status_code == 200


# ---------------------------------------------------------------------------
# CSRF: cookie auth on state-changing methods requires the custom header
# ---------------------------------------------------------------------------


def test_cookie_write_without_csrf_header_is_rejected(client):
    _register_and_login(client)
    res = client.post(
        "/api/versions/", json={"name": "v1", "prompt_text": "hello"}
    )
    assert res.status_code == 403
    assert "X-Requested-With" in res.json()["detail"]


def test_cookie_write_with_csrf_header_succeeds(client):
    _register_and_login(client)
    res = client.post(
        "/api/versions/",
        json={"name": "v1", "prompt_text": "hello"},
        headers=CSRF,
    )
    assert res.status_code == 201


def test_cookie_read_does_not_require_csrf_header(client):
    """GET is safe, so it is not gated -- only state-changing methods are."""
    _register_and_login(client)
    assert client.get("/api/versions/").status_code == 200


def test_bearer_write_does_not_require_csrf_header(client):
    """Header auth is inherently CSRF-immune: a cross-site page cannot set it."""
    from app.services.auth_service import create_access_token

    _register_and_login(client)
    user_id = client.get("/auth/me").json()["id"]

    api_client = TestClient(app, base_url="https://testserver")
    api_client.headers.update(
        {"Authorization": f"Bearer {create_access_token(user_id)}"}
    )
    res = api_client.post(
        "/api/versions/", json={"name": "v1", "prompt_text": "hello"}
    )
    assert res.status_code == 201
