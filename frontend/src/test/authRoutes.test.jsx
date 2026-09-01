import { render, screen, waitFor } from "@testing-library/react";
import { describe, test, expect, vi, beforeEach, afterEach } from "vitest";

import App from "../App";
import { AUTH_ERROR_MESSAGES } from "../oauthErrors";

/*
 * The API redirects into two SPA paths that did not exist before OAuth:
 * /login (where failures land, carrying ?auth_error=) and /link-account (where
 * a password-protected match is confirmed). If either fell through to the
 * catch-all route, a real OAuth failure would silently bounce the user to the
 * editor or the home page with nothing shown. These drive the app's own
 * BrowserRouter through jsdom's history, which is what the redirect does.
 */

beforeEach(() => {
  global.fetch = vi.fn();
});

afterEach(() => {
  window.history.pushState({}, "", "/");
});

function renderAt(path) {
  window.history.pushState({}, "", path);
  return render(<App />);
}

function signedOut() {
  // getMe() -> null: no session, which is the state every one of these
  // redirects arrives in.
  fetch.mockResolvedValue({ ok: false, status: 401, json: async () => ({}) });
}

describe("/login", () => {
  test("renders the sign-in screen rather than falling through", async () => {
    signedOut();
    renderAt("/login");

    await waitFor(() => expect(screen.getByTestId("guest-btn")).toBeInTheDocument());
    expect(screen.getByTestId("google-btn")).toBeInTheDocument();
  });

  test("surfaces an auth_error carried in the URL", async () => {
    signedOut();
    renderAt("/login?auth_error=invalid_state");

    await waitFor(() =>
      expect(screen.getByText(AUTH_ERROR_MESSAGES.invalid_state)).toBeInTheDocument()
    );
  });
});

describe("/link-account", () => {
  test("renders the confirmation step for a signed-out visitor", async () => {
    // getMe() first (401), then the pending-link lookup.
    fetch
      .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ provider: "google", email: "ada@example.com" }),
      });

    renderAt("/link-account");

    // Reaching this page without a session is the whole point: the session is
    // what the password is about to create.
    await waitFor(() =>
      expect(screen.getByTestId("link-password")).toBeInTheDocument()
    );
    expect(screen.getByTestId("link-explainer")).toHaveTextContent("ada@example.com");
  });
});
