"""Password length is capped at bcrypt's real limit: 72 BYTES.

The schema previously allowed 128 characters. bcrypt raises ValueError above 72
bytes, so anything in between became an unhandled 500 -- on register, and on
login for any account that had somehow been created.
"""

import pytest

from app.schemas.auth import MAX_PASSWORD_BYTES

# 4 bytes each in UTF-8: 25 characters, 100 bytes. A character-based cap of 72
# would wave this straight through to the crash.
MULTIBYTE_PASSWORD = "😀" * 25


def _register(client, email, password):
    return client.post("/auth/register", json={"email": email, "password": password})


def test_password_at_the_limit_is_accepted(client):
    res = _register(client, "atlimit@example.com", "x" * MAX_PASSWORD_BYTES)
    assert res.status_code == 201


def test_password_one_byte_over_is_rejected_cleanly(client):
    res = _register(client, "overlimit@example.com", "x" * (MAX_PASSWORD_BYTES + 1))
    assert res.status_code == 422, "should be a validation error, not a 500"


@pytest.mark.parametrize("length", [73, 100, 128])
def test_previously_500ing_lengths_now_validate(client, length):
    """128 was the old cap, so these lengths used to reach bcrypt and crash."""
    res = _register(client, f"len{length}@example.com", "x" * length)
    assert res.status_code == 422


def test_limit_is_measured_in_bytes_not_characters(client):
    assert len(MULTIBYTE_PASSWORD) < MAX_PASSWORD_BYTES, "must be under the char count"
    assert len(MULTIBYTE_PASSWORD.encode("utf-8")) > MAX_PASSWORD_BYTES

    res = _register(client, "emoji@example.com", MULTIBYTE_PASSWORD)
    assert res.status_code == 422


def test_error_message_explains_the_byte_limit(client):
    res = _register(client, "message@example.com", "x" * 100)
    detail = str(res.json()["detail"])
    assert "72 bytes" in detail
    assert "100" in detail


def test_login_with_over_long_password_does_not_500(client):
    """Login validated the same field, so it crashed the same way."""
    res = client.post(
        "/auth/login",
        json={"email": "someone@example.com", "password": "x" * 100},
    )
    assert res.status_code == 422


def test_short_password_still_rejected(client):
    """The lower bound is unchanged."""
    res = _register(client, "short@example.com", "abc")
    assert res.status_code == 422
