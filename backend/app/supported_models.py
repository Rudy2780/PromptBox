'''
Single source of truth for the models supported by each LLM provider.

Note: the frontend keeps its own copy of this list in
frontend/src/components/ModelSelector.jsx — update both together.
'''

SUPPORTED_MODELS = {
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
    ],
    "anthropic": [
        "claude-opus-4-7",
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
    ],
    "gemini": [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
    ],
}

SUPPORTED_OPENAI_MODELS = frozenset(SUPPORTED_MODELS["openai"])
SUPPORTED_ANTHROPIC_MODELS = frozenset(SUPPORTED_MODELS["anthropic"])
SUPPORTED_GEMINI_MODELS = frozenset(SUPPORTED_MODELS["gemini"])
