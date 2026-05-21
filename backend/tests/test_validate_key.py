'''
The test_proiver_key function is mocked so tests don't make real API calls.

Run using:
pytest tests/test_validate_key.py -v
'''
from unittest.mock import AsyncMock, patch

def test_valid_key_returns_200(client):
    '''When the provider accepts the key, return 200 with status and provider name'''
    
    with patch("app.api.routes_validate_key.test_provider_key", new_callable=AsyncMock, return_value=True):
        res = client.post("/api/validate-key", json={
            "provider": "openai",
            "api_key": "sk-test-valid-key-123"
        })
        assert res.status_code == 200
        assert res.json()["status"] == "valid"
        assert res.json()["provider"] == "openai"

def test_invalid_key_returns_401(client):
    '''When the provider rejects the key, return 401.'''
    
    with patch("app.api.routes_validate_key.test_provider_key", new_callable=AsyncMock, return_value=False):
        res = client.post("/api/validate-key", json={
            "provider": "openai",
            "api_key": "sk-invalid-key"
        })
        assert res.status_code == 401

def test_missing_key_returns_422(client):
    '''When api_key field is missing from request, Pydantic returns 422 automatically.'''
    
    res = client.post("/api/validate-key", json={
        "provider": "openai"
    })
    assert res.status_code == 422
    
def test_unsupported_model_returns_400(client):
    '''When provider is not in SUPPOrtED_MODELS list, reutrn 400.'''
    
    res = client.post("/api/validate-key", json={
        "provider": "unsupported-model",
        "api_key": "sk-some-key"
    })
    assert res.status_code == 400
    assert res.json()["detail"] == "Unsupported model"
    
