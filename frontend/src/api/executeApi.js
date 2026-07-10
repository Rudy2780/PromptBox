import { API_BASE } from "./config";


/**
 * Execute a single prompt against one LLM model.
 * @param {Object} params
 * @param {string} params.prompt - The prompt text to send
 * @param {string} params.model - Model identifier (e.g. "gpt-4o", "gemini-2.5-flash")
 * @param {string} params.apiKey - The provider API key
 * @returns {Promise<{model: string, response_text: string, latency: number}>} Model response with latency in seconds
 * @throws {Error} Server error detail message on non-OK responses
 */
export async function executePrompt({ prompt, model, apiKey }) {
  const response = await fetch(`${API_BASE}/api/execute`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      prompt,
      model,
      api_key: apiKey,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    const detail = data && data.detail ? data.detail : "Execution failed.";
    throw new Error(detail);
  }

  return data;
}


/**
 * Execute a prompt against multiple models in a single batch request.
 * @param {Object} params
 * @param {string} params.prompt - The prompt text to send
 * @param {string[]} params.models - Array of model identifiers to execute against
 * @param {Object<string, string>} params.apiKeys - Map of provider name to API key
 * @returns {Promise<Array<{model: string, response_text: string, latency: number}>>} Array of model responses
 * @throws {Error} Server error detail message on non-OK responses
 */
export async function executeBatch({ prompt, models, apiKeys }) {
  const response = await fetch(`${API_BASE}/api/prompt`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      prompt,
      models,
      api_keys: apiKeys,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    const detail = data && data.detail ? data.detail : "Execution failed.";
    throw new Error(detail);
  }

  return data.responses || [];
}

