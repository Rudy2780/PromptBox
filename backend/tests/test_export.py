"""
Tests for GET /api/export/:id endpoint.
"""
import pytest

def register_and_get_headers(client, email="exportuser@example.com", password="password123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_res = client.post("/auth/login", json={"email": email, "password": password})
    token = login_res.json()["token"]
    return {"Authorization": f"Bearer {token}"}

VALID_VERSION = {
    "name": "Export Test Prompt",
    "prompt_text": "Explain quicksort",
    "response_text": "Quicksort is a divide-and-conquer algorithm.",
    "response_model": "gpt-4",
    "response_latency": 0.5
}

@pytest.fixture
def test_version_id(client):
    headers = register_and_get_headers(client, email="exportsetup@example.com")
    res = client.post("/api/versions/", json=VALID_VERSION, headers=headers)
    return res.json()["id"], headers

def test_export_txt_returns_200(client, test_version_id):
    version_id, headers = test_version_id
    res = client.get(f"/api/export/{version_id}?format=txt", headers=headers)
    
    assert res.status_code == 200
    assert res.headers["content-type"] == "text/plain; charset=utf-8"
    assert "attachment" in res.headers["content-disposition"]
    
    content = res.text
    assert "Prompt:" in content
    assert "Explain quicksort" in content
    assert "Response (" in content
    assert "Quicksort is" in content

def test_export_md_returns_200(client, test_version_id):
    version_id, headers = test_version_id
    res = client.get(f"/api/export/{version_id}?format=md", headers=headers)
    
    assert res.status_code == 200
    assert res.headers["content-type"] == "text/markdown; charset=utf-8"
    assert "attachment" in res.headers["content-disposition"]
    
    content = res.text
    assert "# Export Test Prompt" in content
    assert "## Prompt" in content
    assert "Explain quicksort" in content

def test_export_json_returns_200(client, test_version_id):
    version_id, headers = test_version_id
    res = client.get(f"/api/export/{version_id}?format=json", headers=headers)
    
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/json"
    assert "attachment" in res.headers["content-disposition"]
    
    data = res.json()
    assert data["prompt_text"] == "Explain quicksort"
    assert data["response_text"] == "Quicksort is a divide-and-conquer algorithm."
    assert data["response_model"] == "gpt-4"
    assert "created_at" in data

def test_export_unsupported_format_returns_400(client, test_version_id):
    version_id, headers = test_version_id
    res = client.get(f"/api/export/{version_id}?format=pdf", headers=headers)
    assert res.status_code == 400

def test_export_unauthenticated_returns_401(client, test_version_id):
    version_id, _ = test_version_id
    res = client.get(f"/api/export/{version_id}?format=txt")
    assert res.status_code in (401, 403)
