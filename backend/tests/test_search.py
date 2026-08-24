def register_and_get_headers(client, email="searchuser@example.com", password="password123"):
    """Register + log in, returning the headers callers must send.

    Authentication now travels in an httpOnly cookie, which the TestClient's
    cookie jar stores and replays automatically -- so the returned dict carries
    only the CSRF header that cookie-authenticated writes require.
    """
    client.post("/auth/register", json={"email": email, "password": password})
    login_res = client.post("/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200, f"login failed: {login_res.text}"
    return {"X-Requested-With": "PromptBox"}

def save_version(client, headers, name="test prompt", prompt_text="hello", tag=None):
    body = {"name": name, "prompt_text": prompt_text}
    if tag is not None:
        body["tag"] = tag
    res = client.post("/api/versions/", json=body, headers=headers)
    assert res.status_code == 201
    return res.json()

def test_search_by_name_returns_matching_versions(client):
    headers = register_and_get_headers(client, email="search1@example.com")
    save_version(client, headers, name="Quicksort explanation")
    save_version(client, headers, name="Bubble sort explanation")
    
    res = client.get("/api/versions/?search=quicksort", headers=headers)
    
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert "quicksort" in data[0]["name"].lower()
    
def test_search_by_tag_returns_matching_versions(client):
    headers = register_and_get_headers(client, email="search2@example.com")
    save_version(client, headers, name="prompt A", tag="Final")
    save_version(client, headers, name="prompt B", tag="draft")
    
    res = client.get("/api/versions/?search=final", headers=headers)
    
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["tag"].lower() == "final"
    
def test_search_no_match_returns_empty_list(client):
    headers = register_and_get_headers(client, email="search3@example.com")
    save_version(client, headers, name="some prompt", tag="draft")
    
    res = client.get("/api/versions/?search=nonexistent", headers=headers)
    
    assert res.status_code == 200
    assert res.json() == []
    
def test_search_does_not_return_other_userversions(make_authed_client):
    """One user's search must not reach another user's versions.

    Two independent clients, because a session is now a cookie: logging both
    users in through one client would overwrite the first session with the
    second and the test would silently stop testing isolation.
    """
    client_a = make_authed_client("search4@example.com")
    client_b = make_authed_client("search5@example.com")
    csrf = {"X-Requested-With": "PromptBox"}

    save_version(client_a, csrf, name="shared keyword prompt", tag="secret")

    res = client_b.get("/api/versions/?search=shared")
    
    assert res.status_code == 200
    assert res.json() == []
