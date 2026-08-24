import { apiFetch, apiJson } from "./http.js";

/**
 * @typedef {Object} VersionResponse
 * @property {number} id
 * @property {string} name
 * @property {string|null} tag
 * @property {string} prompt_text
 * @property {string|null} response_text
 * @property {string|null} response_model
 * @property {number|null} response_latency
 * @property {string} created_at
 */

/**
 * Save a new prompt version to the user's account.
 * @param {Object} payload
 * @param {string} payload.name - Version name (1-255 characters)
 * @param {string|null} payload.tag - Optional tag (max 32 characters)
 * @param {string} payload.prompt_text - The prompt content
 * @param {string|null} payload.response_text - Optional LLM response text
 * @param {string|null} payload.response_model - Optional model identifier
 * @param {number|null} payload.response_latency - Optional response time in seconds
 * @returns {Promise<VersionResponse>} The created version with id and created_at
 * @throws {Error} Server error detail message on non-OK responses
 */
export async function saveVersion(payload) {
    return apiJson("/api/versions/", {
        method: "POST",
        body: payload,
        errorMessage: "Failed to save version",
    });
}

/**
 * Fetch all saved versions for the authenticated user, optionally filtered by search.
 * @param {string} [search] - Optional search string to filter by name or tag
 * @returns {Promise<Array<VersionResponse>>} Array of matching versions
 * @throws {Error} Server error detail message on non-OK responses
 */
export async function getVersions(search) {
    const query = search ? `?search=${encodeURIComponent(search)}` : "";
    return apiJson(`/api/versions/${query}`, {
        errorMessage: "Failed to fetch versions",
    });
}

/**
 * Fetch a single version by ID.
 * @param {number} id - The version ID to retrieve
 * @returns {Promise<VersionResponse>} The requested version
 * @throws {Error} Server error detail message if not found or unauthorized
 */
export async function getVersion(id) {
    return apiJson(`/api/versions/${id}`, {
        errorMessage: "Failed to fetch version",
    });
}

/**
 * Update a version's name and tag.
 * @param {number} id - The version ID to update
 * @param {Object} payload
 * @param {string} payload.name - New version name
 * @param {string|null} payload.tag - New tag, or null to clear
 * @returns {Promise<VersionResponse>} The updated version
 * @throws {Error} Server error detail message on non-OK responses
 */
export async function updateVersion(id, payload) {
    return apiJson(`/api/versions/${id}`, {
        method: "PATCH",
        body: payload,
        errorMessage: "Failed to update version",
    });
}

/**
 * Delete a saved version.
 * @param {number} id - The version ID to delete
 * @returns {Promise<void>}
 * @throws {Error} Server error detail message if not found or unauthorized
 */
export async function deleteVersion(id) {
    const res = await apiFetch(`/api/versions/${id}`, { method: "DELETE" });

    if (!res.ok) {
        let detail = "Failed to delete version";
        try {
            const data = await res.json();
            detail = data?.detail || detail;
        } catch {
            // no body
        }
        throw new Error(detail);
    }
}
