"""LIKE metacharacters in search text must be treated as literals.

Not an injection issue -- the value is bound, not interpolated -- but an
unescaped "%" matched every row, so searching for a literal percent sign
returned the user's entire library instead of nothing.
"""

import pytest

CSRF = {"X-Requested-With": "PromptBox"}


@pytest.fixture
def seeded(client):
    creds = {"email": "searchesc@example.com", "password": "password123"}
    client.post("/auth/register", json=creds)
    assert client.post("/auth/login", json=creds).status_code == 200
    client.headers.update(CSRF)

    for name, tag in [
        ("Quicksort explanation", "draft"),
        ("Bubble sort", "final"),
        ("100% coverage plan", "draft"),
        ("snake_case naming", "draft"),
    ]:
        res = client.post(
            "/api/versions/",
            json={"name": name, "tag": tag, "prompt_text": "x"},
        )
        assert res.status_code == 201
    return client


def test_percent_is_not_a_wildcard(seeded):
    """"%" used to match everything; it should match only the literal."""
    res = seeded.get("/api/versions/?search=%25")  # URL-encoded '%'
    assert res.status_code == 200
    names = [v["name"] for v in res.json()]
    assert names == ["100% coverage plan"], names


def test_underscore_is_not_a_single_character_wildcard(seeded):
    res = seeded.get("/api/versions/?search=snake_case")
    assert res.status_code == 200
    assert [v["name"] for v in res.json()] == ["snake_case naming"]


def test_underscore_does_not_match_arbitrary_characters(seeded):
    """"snake?case" style matching must not happen: 'snakexcase' has no row,
    and a wildcard underscore would have matched 'snake_case naming'."""
    res = seeded.get("/api/versions/?search=snakexcase")
    assert res.json() == []


def test_backslash_is_handled(seeded):
    """The escape character itself must be escaped, or the query errors."""
    res = seeded.get("/api/versions/?search=%5C")  # a single backslash
    assert res.status_code == 200
    assert res.json() == []


def test_ordinary_search_still_works(seeded):
    res = seeded.get("/api/versions/?search=quicksort")
    assert [v["name"] for v in res.json()] == ["Quicksort explanation"]


def test_tag_search_still_works(seeded):
    res = seeded.get("/api/versions/?search=final")
    assert [v["name"] for v in res.json()] == ["Bubble sort"]
