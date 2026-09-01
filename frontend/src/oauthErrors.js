/**
 * Plain-language wording for the OAuth failure slugs the API redirects with.
 *
 * The backend never sends prose. It sends one of a closed set of opaque codes
 * (see backend/app/services/oauth_service.py) precisely because the code
 * travels in a URL, which is written to browser history, sent in Referer
 * headers, and logged by every proxy along the way. The sentence a person
 * reads is chosen here instead, where it costs nothing to change and can say
 * something useful about what to do next.
 *
 * Keep this table in step with ERROR_CODES on the backend.
 */
export const AUTH_ERROR_MESSAGES = {
    access_denied:
        "Sign-in was cancelled. You can try again, or continue with email instead.",
    invalid_state:
        "That sign-in link could not be verified — it may have expired or been opened out of order. Please try again.",
    email_unverified:
        "Your provider did not confirm a verified email address for that account. Verify your email with them and try again, or sign in with email instead.",
    provider_error:
        "The sign-in provider could not be reached just now. Please try again in a moment.",
    provider_unavailable: "That sign-in method is not available on this server.",
    link_expired:
        "That sign-in took too long to confirm. Please start again.",
    invalid_password: "That password is not correct.",
};

const FALLBACK =
    "Sign-in could not be completed. Please try again, or continue with email instead.";

/**
 * The sentence to show for a failure code.
 *
 * Unknown codes fall back rather than rendering the raw slug: the parameter is
 * attacker-controllable (anyone can put ?auth_error=... in a link they send),
 * so it must never be echoed into the page.
 *
 * @param {string|null|undefined} code
 * @returns {string|null} The message, or null when there is no error.
 */
export function authErrorMessage(code) {
    if (!code) return null;
    return AUTH_ERROR_MESSAGES[code] ?? FALLBACK;
}

/** Codes the user can fix by retrying in place, rather than starting over. */
export const RETRYABLE_ERRORS = new Set(["invalid_password"]);
