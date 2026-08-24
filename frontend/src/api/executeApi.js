import { apiJson } from "./http.js";

/**
 * Execute a prompt against multiple models in a single batch request.
 * Requires an authenticated session. The server accepts at most 4 distinct
 * models per request and deduplicates the list.
 * @param {Object} params
 * @param {string} params.prompt - The prompt text to send
 * @param {string[]} params.models - Array of model identifiers to execute against
 * @param {Object<string, string>} params.apiKeys - Map of provider name to API key
 * @returns {Promise<Array<{model: string, response_text: string, latency: number}>>} Array of model responses
 * @throws {Error} Server error detail message on non-OK responses
 */
export async function executeBatch({ prompt, models, apiKeys }) {
  const data = await apiJson("/api/prompt", {
    method: "POST",
    body: { prompt, models, api_keys: apiKeys },
    errorMessage: "Execution failed.",
  });
  return data?.responses || [];
}
