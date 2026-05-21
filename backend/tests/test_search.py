import pytest

def register_and_get_headers(client, email="searchuser@example.com", password="password123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_res = client.post("/auth/login", json={"email": email, "password": password})
    token = login_res.json()["token"]
    return {"Authorization": f"Bearer {token}"}

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
    
def test_search_does_not_return_other_userversions(client):
    headers_a = register_and_get_headers(client, email="search4@example.com")
    headers_b = register_and_get_headers(client, email="search5@example.com")
    
    save_version(client, headers_a, name="shared keyword prompt", tag="secret")
    
    res = client.get("/api/versions/?search=shared", headers=headers_b)
    
    assert res.status_code == 200
    assert res.json() == []
