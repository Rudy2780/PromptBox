'''
This module handles validating user-provided API keys for supported LLM providers
It is used in the /api/validate-key endpoint in the routes_validate_key.py

The user selects a provider and enters their api key
test_provider_key routes to the correct specific validation function
each provider function uses the cheapests API call to check it the key is valid
Returns True if the key is valid, False if not

This module no longer imports the vendor SDKs. It previously built its own
openai.OpenAI / anthropic.Anthropic / genai.Client instances, duplicating what
app/providers/* already does, so each provider had two client-construction
paths that could (and did) drift apart. Validation now goes through the same
adapters that execution uses.
'''

from app.providers.registry import provider_for_name


async def test_provider_key(provider: str, api_key: str) -> bool:
    '''Makes a lightweight API call to provider to verify the status of the key'''
    adapter = provider_for_name(provider, api_key)
    if adapter is None:
        return False
    return adapter.validate_key()
