"""Account enumeration resistance and auth throttling."""

from app.models.user import UserInfo

CREDS = {"email": "enum@example.com", "password": "password123"}


def test_registration_is_indistinguishable_for_taken_addresses(client):
    """Status code and body must be byte-identical either way."""
    first = client.post("/auth/register", json=CREDS)
    second = client.post("/auth/register", json=CREDS)

    assert first.status_code == second.status_code
    assert first.json() == second.json()


def test_duplicate_registration_creates_no_second_row(client, db_session):
    client.post("/auth/register", json=CREDS)
    client.post("/auth/register", json=CREDS)

    count = db_session.query(UserInfo).filter(UserInfo.email == CREDS["email"]).count()
    assert count == 1


def test_duplicate_registration_does_not_change_the_password(client):
    client.post("/auth/register", json=CREDS)
    client.post(
        "/auth/register",
        json={"email": CREDS["email"], "password": "attacker-chosen-pw"},
    )

    hijacked = client.post(
        "/auth/login",
        json={"email": CREDS["email"], "password": "attacker-chosen-pw"},
    )
    assert hijacked.status_code == 401, "re-registration must not reset the password"


def test_login_response_does_not_distinguish_unknown_from_wrong_password(client):
    client.post("/auth/register", json=CREDS)

    wrong_password = client.post(
        "/auth/login", json={"email": CREDS["email"], "password": "wrongpassword"}
    )
    unknown_user = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "wrongpassword"}
    )

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()


def test_login_is_throttled(client, rate_limited):
    """Password guessing gets a small number of attempts per minute."""
    client.post("/auth/register", json=CREDS)

    # Passwords must clear the 8-character minimum, or they are rejected at
    # validation (422) before the handler -- and therefore before the limiter.
    statuses = [
        client.post(
            "/auth/login", json={"email": CREDS["email"], "password": f"guess-{i:04d}"}
        ).status_code
        for i in range(20)
    ]

    assert 422 not in statuses, "test passwords must be long enough to be evaluated"
    assert 429 in statuses, f"login was never throttled: {statuses}"
    assert statuses[0] == 401, "the first attempt should be evaluated normally"


def test_registration_is_throttled(client, rate_limited):
    statuses = [
        client.post(
            "/auth/register",
            json={"email": f"spam{i}@example.com", "password": "password123"},
        ).status_code
        for i in range(20)
    ]

    assert 429 in statuses, f"registration was never throttled: {statuses}"
