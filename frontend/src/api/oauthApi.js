import { apiJson } from "./http.js";
import { API_BASE } from "./config.js";

/**
 * The URL that begins a provider sign-in.
 *
 * This is a destination for the browser to *travel* to, not an endpoint to
 * fetch. The flow needs a top-level navigation: the user has to see the
 * provider's consent screen, and the browser has to follow the redirect back
 * to the API so the callback can set an httpOnly cookie on that origin. An XHR
 * could do neither, and there would be nothing in the response for script to
 * read even if it could.
 *
 * @param {"github"|"google"} provider
 * @returns {string} Absolute URL on the API origin.
 */
export function oauthLoginUrl(provider) {
    return `${API_BASE}/auth/${provider}/login`;
}

/**
 * Describe the sign-in that is waiting for a password.
 *
 * Reached when a provider login matched an existing password-protected
 * account: the API links nothing and issues no session until the user proves
 * the password. The pending attempt lives in an httpOnly cookie, so this call
 * is the only way the page can learn which account and provider it is about.
 *
 * @returns {Promise<{provider: string, email: string}>}
 * @throws {Error} With `authError` set to the API's failure code.
 */
export function getPendingLink() {
    return apiJson("/auth/link/pending", {
        errorMessage: "There is no sign-in waiting to be confirmed",
    });
}

/**
 * Confirm a pending link with the account's existing password.
 *
 * On success the API writes the identity row and sets the ordinary session
 * cookie — the same one email/password login issues.
 *
 * @param {string} password
 * @returns {Promise<{status: string, email: string}>}
 * @throws {Error} With `authError` set to the API's failure code.
 */
export function confirmLink(password) {
    return apiJson("/auth/link/confirm", {
        method: "POST",
        body: { password },
        errorMessage: "Could not confirm that sign-in",
    });
}

/**
 * Abandon a pending link. Nothing was written, so nothing is undone.
 * @returns {Promise<{status: string}>}
 */
export function cancelLink() {
    return apiJson("/auth/link/cancel", {
        method: "POST",
        errorMessage: "Could not cancel",
    });
}
