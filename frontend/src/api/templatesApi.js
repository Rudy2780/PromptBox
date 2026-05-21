const API_BASE = "https://promptbox-9d83.onrender.com"


/**
 * Fetch prompt templates, optionally filtered by category.
 * @param {string|null} [category=null] - Filter by category ("reasoning" | "structure" | "task"), or null for all
 * @returns {Promise<Array<{id: number, name: string, category: string, content: string}>>} Array of templates
 * @throws {Error} Server error detail message on non-OK responses
 */
export async function getTemplates(category = null) {
    const url = new URL(`${API_BASE}/api/templates/`)
    if (category) {
        url.searchParams.set("category", category)
    }
    const res = await fetch(url.toString())
    const data = await res.json()
    if (!res.ok) {
        throw new Error(data?.detail || "Failed to fetch templates")
    }
    return data
}


/**
 * Fetch a single template by ID.
 * @param {number} id - The template ID to retrieve
 * @returns {Promise<{id: number, name: string, category: string, content: string}>} The requested template
 * @throws {Error} Server error detail message if not found
 */
export async function getTemplate(id) {
    const res = await fetch(`${API_BASE}/api/templates/${id}`)
    const data = await res.json()
    if (!res.ok) {
        throw new Error(data?.detail || "Failed to fetch template")
    }
    return data
}
