import { apiJson } from "./http.js";

/**
 * Fetch prompt templates, optionally filtered by category.
 * @param {string|null} [category=null] - Filter by category ("reasoning" | "structure" | "task"), or null for all
 * @returns {Promise<Array<{id: number, name: string, category: string, content: string}>>} Array of templates
 * @throws {Error} Server error detail message on non-OK responses
 */
export async function getTemplates(category = null) {
    const query = category ? `?category=${encodeURIComponent(category)}` : "";
    return apiJson(`/api/templates/${query}`, {
        errorMessage: "Failed to fetch templates",
    });
}

/**
 * Fetch a single template by ID.
 * @param {number} id - The template ID to retrieve
 * @returns {Promise<{id: number, name: string, category: string, content: string}>} The requested template
 * @throws {Error} Server error detail message if not found
 */
export async function getTemplate(id) {
    return apiJson(`/api/templates/${id}`, {
        errorMessage: "Failed to fetch template",
    });
}
