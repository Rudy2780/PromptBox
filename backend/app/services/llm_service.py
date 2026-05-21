'''
This module handles validating user-provided API keys for supported LLM providers
It is used in the /api/validate-key endpoint in the routes_validate_key.py

The user selects a provider and enters their api key
test_provider_key routes to the correct specific validation function
each provider function uses the cheapests API call to check it the key is valid
Returns True if the key is valid, False if not

'''



import openai
import anthropic
from google import genai

async def test_provider_key(provider: str, api_key: str) -> bool: 
    '''Makes a lightweight API call to provider to verify the status of the key'''
    try:
        if provider == "openai":
            return await test_openai_key(api_key)
        elif provider == "anthropic":
            return await test_anthropic_key(api_key)
        elif provider == "gemini": 
            return await test_gemini_key(api_key)
        else:
            return False
    except Exception:
        return False
    
async def test_openai_key(api_key: str) -> bool:
    try:
        client = openai.OpenAI(api_key=api_key)
        client.models.list()
        return True
    except openai.AuthenticationError:
        return False

async def test_anthropic_key(api_key: str) -> bool:
    try:
        client = anthropic.Anthropic(api_key=api_key)
        client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}]
        )
        return True
    except anthropic.AuthenticationError:
        return False
    
async def test_gemini_key(api_key: str) -> bool:
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.list()
        return True
    except Exception:
        return False

async def test_anthropic_key(api_key: str) -> bool:
    try:
        client = anthropic.Anthropic(api_key=api_key)
        client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}]
        )
        return True
    except anthropic.AuthenticationError as e:
        print(f"Anthropic auth error: {e}")
        return False
    except Exception as e:
        print(f"Anthropic other error: {type(e).__name__}: {e}")
        return False
