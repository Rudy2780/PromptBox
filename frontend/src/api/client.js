import { apiFetch, API_BASE } from "./http.js";

export { API_BASE };

/**
 * Check the health status of the backend server.
 * @returns {Promise<{status: string}>} Server health status object
 */
export async function getHealth() {
    const res = await apiFetch("/health");
    return res.json();
}

/**
 * Validate an LLM provider API key by making a lightweight test call server-side.
 * Requires an authenticated session.
 * @param {string} provider - Provider name ("openai" | "gemini" | "anthropic")
 * @param {string} apiKey - The API key to validate
 * @returns {Promise<{status: number, data: {status: string, provider: string}}>} Status code and response body
 */
export async function validateKey(provider, apiKey) {
    const res = await apiFetch("/api/validate-key", {
        method: "POST",
        body: { provider, api_key: apiKey },
    });
    return { status: res.status, data: await res.json() };
}
