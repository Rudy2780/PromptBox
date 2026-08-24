import { apiJson } from "./http.js";

/**
 * Register a new account. Does not sign the user in.
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{status: string, email: string}>}
 * @throws {Error} Server error detail message on non-OK responses
 */
export function register(email, password) {
    return apiJson("/auth/register", {
        method: "POST",
        body: { email, password },
        errorMessage: "Registration failed",
    });
}

/**
 * Sign in. On success the server sets an httpOnly session cookie; there is no
 * token in the response for the page to read or store.
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{status: string, email: string}>}
 * @throws {Error} Server error detail message on non-OK responses
 */
export function login(email, password) {
    return apiJson("/auth/login", {
        method: "POST",
        body: { email, password },
        errorMessage: "Login failed",
    });
}

/**
 * Sign out. The server expires the session cookie; clearing it client-side is
 * not possible (and would not be trustworthy) because the cookie is httpOnly.
 * @returns {Promise<{status: string}>}
 */
export function logout() {
    return apiJson("/auth/logout", {
        method: "POST",
        errorMessage: "Logout failed",
    });
}

/**
 * Return the currently signed-in user, or null if there is no valid session.
 * Used on page load to restore sign-in state, since the page cannot inspect
 * the httpOnly cookie itself.
 * @returns {Promise<{id: number, email: string}|null>}
 */
export async function getMe() {
    try {
        return await apiJson("/auth/me", { errorMessage: "Not signed in" });
    } catch {
        return null;
    }
}
