const API_BASE = "https://promptbox-9d83.onrender.com";


/**
 * Check the health status of the backend server.
 * @returns {Promise<{status: string}>} Server health status object
 */
export async function getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
}

/**
 * Validate an LLM provider API key by making a lightweight test call server-side.
 * @param {string} provider - Provider name ("openai" | "gemini" | "anthropic")
 * @param {string} apiKey - The API key to validate
 * @returns {Promise<{status: number, data: {status: string, provider: string}}>} Status code and response body
 */
export async function validateKey(provider, apiKey) {
    const res = await fetch(`${API_BASE}/api/validate-key`, {
        method: "POST",
        headers: { "Content-Type": "application/json"},
        body: JSON.stringify({provider, api_key: apiKey})
    });
    return { status: res.status, data: await res.json() };
}
