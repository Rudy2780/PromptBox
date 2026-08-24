# Known Bugs

- `backend/app/providers/anthropic_provider.py` raises `ProviderAuthError` (HTTP 401) where the OpenAI and Gemini providers raise `ProviderError` (HTTP 502) for generic errors — inconsistent error handling, should likely be `ProviderError`.
- `backend/app/main.py` `create_all` imports the `user` and `prompt_version` models but not `template` — the templates table only exists if the seed script runs first, a deployment-order risk.
11