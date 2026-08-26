import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { apiFetch, API_BASE } from "../api/http";
import { getMe, logout } from "../api/authApi";
import { GUEST_SESSION } from "../session";
import Login from "../components/Login";

beforeEach(() => {
  global.fetch = vi.fn();
});

// ---------------------------------------------------------------------------
// Transport: the cookie can only be sent if every request opts in
// ---------------------------------------------------------------------------

describe("apiFetch", () => {
  it("sends credentials so the httpOnly session cookie is included", async () => {
    fetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    await apiFetch("/anything");
    const [, options] = fetch.mock.calls[0];
    expect(options.credentials).toBe("include");
  });

  it("attaches the CSRF header to state-changing requests", async () => {
    fetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    await apiFetch("/anything", { method: "POST", body: { a: 1 } });
    const [, options] = fetch.mock.calls[0];
    expect(options.headers["X-Requested-With"]).toBe("PromptBox");
  });

  it("does not attach the CSRF header to safe requests", async () => {
    fetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    await apiFetch("/anything");
    const [, options] = fetch.mock.calls[0];
    expect(options.headers["X-Requested-With"]).toBeUndefined();
  });

  it("resolves paths against API_BASE", async () => {
    fetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    await apiFetch("/health");
    expect(fetch.mock.calls[0][0]).toBe(`${API_BASE}/health`);
  });
});

// ---------------------------------------------------------------------------
// Session restoration
// ---------------------------------------------------------------------------

describe("getMe", () => {
  it("returns the user when a session cookie is valid", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 1, email: "a@b.com" }),
    });
    await expect(getMe()).resolves.toEqual({ id: 1, email: "a@b.com" });
  });

  it("returns null rather than throwing when there is no session", async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Not authenticated" }),
    });
    await expect(getMe()).resolves.toBeNull();
  });
});

describe("logout", () => {
  it("asks the server to clear the cookie, since the page cannot", async () => {
    fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ status: "logged_out" }) });
    await logout();
    const [url, options] = fetch.mock.calls[0];
    expect(url).toBe(`${API_BASE}/auth/logout`);
    expect(options.method).toBe("POST");
    expect(options.credentials).toBe("include");
  });
});

// ---------------------------------------------------------------------------
// Login: no token reaches the page, and guest is an explicit state
// ---------------------------------------------------------------------------

describe("Login", () => {
  const renderLogin = (onAuth) =>
    render(
      <MemoryRouter>
        <Login onAuth={onAuth} />
      </MemoryRouter>
    );

  it("signs in without receiving or storing a token", async () => {
    const onAuth = vi.fn();
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "ok", email: "user@example.com" }),
    });

    renderLogin(onAuth);

    fireEvent.click(screen.getByTestId("email-toggle")); // reveal the email form
    fireEvent.click(screen.getByTestId("login-btn")); // switch to Login mode
    fireEvent.change(screen.getByPlaceholderText("Email Id"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByTestId("login-btn")); // submit

    await waitFor(() => expect(onAuth).toHaveBeenCalled());
    const session = onAuth.mock.calls[0][0];
    expect(session).toEqual({ email: "user@example.com" });
    expect(session).not.toHaveProperty("token");
  });

  it("hands the guest path an explicit marker, not null", async () => {
    const onAuth = vi.fn();
    renderLogin(onAuth);

    fireEvent.click(screen.getByTestId("guest-btn"));

    // The old behaviour passed null, which the dashboard could not tell apart
    // from a signed-in user and which silently blanked every gated panel.
    expect(onAuth).toHaveBeenCalledWith(GUEST_SESSION);
    expect(onAuth).not.toHaveBeenCalledWith(null);
    expect(GUEST_SESSION.isGuest).toBe(true);
  });
});
