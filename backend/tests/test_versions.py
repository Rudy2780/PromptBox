""" 
Tests for POST /api/versions endpoint
"""

def register_and_get_headers(client, email="versionuser@example.com", password="password123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_res = client.post("/auth/login", json={"email": email, "password": password})
    token = login_res.json()["token"]
    return {"Authorization": f"Bearer {token}"}

VALID_VERSION = {
    "name": "v1 - inital draft",
    "tag": "draft",
    "prompt_text": "Explain quicksort in plain English",
}

def test_save_version_returns_201(client):
    headers = register_and_get_headers(client)
    res = client.post("/api/versions/", json=VALID_VERSION, headers=headers)
    
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == VALID_VERSION["name"]
    assert data["tag"] == VALID_VERSION["tag"]
    assert data["prompt_text"] == VALID_VERSION["prompt_text"]
    assert "id" in data
    assert "created_at" in data
    
def test_save_version_missing_prompt_returns_422(client):
    headers = register_and_get_headers(client)
    res = client.post("/api/versions/", json={"name": "v1"}, headers=headers)
    
    assert res.status_code == 422
    
def test_save_version_unauthenticated_returns_401(client):
    res = client.post("/api/versions/", json=VALID_VERSION)
    
    assert res.status_code in (401, 403)
    
def test_get_versions_returns_200_and_list(client):
    headers = register_and_get_headers(client, email="getu1@example.com")
    # Save a version first
    client.post("/api/versions/", json=VALID_VERSION, headers=headers)
    
    res = client.get("/api/versions/", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["name"] == VALID_VERSION["name"]

def test_get_version_by_id_returns_200(client):
    headers = register_and_get_headers(client, email="getu2@example.com")
    save_res = client.post("/api/versions/", json=VALID_VERSION, headers=headers)
    version_id = save_res.json()["id"]
    
    res = client.get(f"/api/versions/{version_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == version_id
    assert data["name"] == VALID_VERSION["name"]

def test_get_version_nonexistent_returns_404(client):
    headers = register_and_get_headers(client, email="getu3@example.com")
    res = client.get("/api/versions/999999", headers=headers)
    assert res.status_code == 404

def test_get_version_unauthenticated_returns_401(client):
    res = client.get("/api/versions/1")
    assert res.status_code in (401, 403)

def test_get_versions_unauthenticated_returns_401(client):
    res = client.get("/api/versions/")
    assert res.status_code in (401, 403)

def test_save_version_tag_too_long_returns_422(client):
    headers = register_and_get_headers(client, email="taglimit@example.com")
    body = {
        "name": "v2",
        "tag": "x" * 33,
        "prompt_text": "Prompt text",
    }
    res = client.post("/api/versions/", json=body, headers=headers)
    assert res.status_code == 422

def test_update_version_name_and_tag_returns_200(client):
    headers = register_and_get_headers(client, email="updatev1@example.com")
    save_res = client.post("/api/versions/", json=VALID_VERSION, headers=headers)
    version_id = save_res.json()["id"]

    update_body = {"name": "v1 - revised", "tag": "final"}
    res = client.patch(f"/api/versions/{version_id}", json=update_body, headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["id"] == version_id
    assert data["name"] == "v1 - revised"
    assert data["tag"] == "final"

def test_update_version_allows_null_tag(client):
    headers = register_and_get_headers(client, email="updatev2@example.com")
    save_res = client.post("/api/versions/", json=VALID_VERSION, headers=headers)
    version_id = save_res.json()["id"]

    res = client.patch(
        f"/api/versions/{version_id}",
        json={"name": "v1 - revised", "tag": None},
        headers=headers,
    )

    assert res.status_code == 200
    assert res.json()["tag"] is None

def test_update_version_tag_too_long_returns_422(client):
    headers = register_and_get_headers(client, email="updatev3@example.com")
    save_res = client.post("/api/versions/", json=VALID_VERSION, headers=headers)
    version_id = save_res.json()["id"]

    res = client.patch(
        f"/api/versions/{version_id}",
        json={"name": "v1", "tag": "x" * 33},
        headers=headers,
    )
    assert res.status_code == 422

def test_delete_version_returns_204_and_removes_from_db(client):
    headers = register_and_get_headers(client, email="deletev1@example.com")
    save_res = client.post("/api/versions/", json=VALID_VERSION, headers=headers)
    version_id = save_res.json()["id"]

    delete_res = client.delete(f"/api/versions/{version_id}", headers=headers)
    assert delete_res.status_code == 204

    fetch_res = client.get(f"/api/versions/{version_id}", headers=headers)
    assert fetch_res.status_code == 404

def test_delete_version_nonexistent_returns_404(client):
    headers = register_and_get_headers(client, email="deletev2@example.com")
    res = client.delete("/api/versions/999999", headers=headers)
    assert res.status_code == 404
