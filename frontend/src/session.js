/**
 * The guest "session".
 *
 * A guest has no server session at all, so every authenticated endpoint will
 * reject them. This marker lets the UI distinguish "browsing as guest" from
 * "signed in" and from "signed out", instead of the previous `null`, which was
 * indistinguishable from an authenticated user with no fields and silently
 * blanked every user-gated panel.
 */
export const GUEST_SESSION = { isGuest: true };
