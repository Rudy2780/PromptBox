import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { describe, test, expect, vi, beforeEach } from "vitest";

import LinkAccount from "../pages/LinkAccount";
import { AUTH_ERROR_MESSAGES } from "../oauthErrors";
import { API_BASE } from "../api/config";

/*
 * The confirmation step. Reaching this page means a provider login matched an
 * address that already has a password: nothing has been linked, and there is
 * no session. The password is what releases both.
 */

beforeEach(() => {
  global.fetch = vi.fn();
});

function jsonResponse(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

function mockPending(body = { provider: "google", email: "ada@example.com" }) {
  fetch.mockResolvedValueOnce(jsonResponse(200, body));
}

function LocationProbe() {
  const location = useLocation();
  return <span data-testid="location">{`${location.pathname}${location.search}`}</span>;
}

function renderPage(onAuth = vi.fn()) {
  render(
    <MemoryRouter initialEntries={["/link-account"]}>
      <LocationProbe />
      <Routes>
        <Route path="/link-account" element={<LinkAccount onAuth={onAuth} />} />
        <Route path="/login" element={<div>sign-in screen</div>} />
        <Route path="/editor" element={<div>editor</div>} />
        <Route path="/" element={<div>home</div>} />
      </Routes>
    </MemoryRouter>
  );
  return onAuth;
}

async function waitForPrompt() {
  await waitFor(() => expect(screen.getByTestId("link-password")).toBeInTheDocument());
}

describe("asking for the password", () => {
  test("names the account and the provider", async () => {
    mockPending();
    renderPage();

    await waitForPrompt();
    const explainer = screen.getByTestId("link-explainer");
    expect(explainer).toHaveTextContent("ada@example.com");
    expect(explainer).toHaveTextContent("Google");
  });

  test("reads the pending link from the API rather than the URL", async () => {
    mockPending();
    renderPage();

    await waitForPrompt();
    // The pending attempt lives in an httpOnly cookie; nothing identifying it
    // was ever put in the address bar.
    const [url, options] = fetch.mock.calls[0];
    expect(url).toBe(`${API_BASE}/auth/link/pending`);
    expect(options.credentials).toBe("include");
    expect(screen.getByTestId("location").textContent).not.toContain("ada@example.com");
  });

  test("renders the GitHub name when that is the provider", async () => {
    mockPending({ provider: "github", email: "ada@example.com" });
    renderPage();

    await waitForPrompt();
    expect(screen.getByTestId("link-explainer")).toHaveTextContent("GitHub");
  });
});

describe("confirming with the correct password", () => {
  test("links, signs in, and lands in the editor", async () => {
    mockPending();
    const onAuth = vi.fn();
    renderPage(onAuth);
    await waitForPrompt();

    fetch.mockResolvedValueOnce(
      jsonResponse(200, { status: "ok", email: "ada@example.com" })
    );
    fireEvent.change(screen.getByTestId("link-password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByTestId("link-confirm"));

    await waitFor(() => expect(onAuth).toHaveBeenCalledWith({ email: "ada@example.com" }));
    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent("/editor")
    );

    const [url, options] = fetch.mock.calls[1];
    expect(url).toBe(`${API_BASE}/auth/link/confirm`);
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ password: "password123" });
    // Cookie-driven write, so it must carry the CSRF header.
    expect(options.headers["X-Requested-With"]).toBe("PromptBox");
  });
});

describe("confirming with the wrong password", () => {
  test("shows the error and stays put so it can be retried", async () => {
    mockPending();
    const onAuth = vi.fn();
    renderPage(onAuth);
    await waitForPrompt();

    fetch.mockResolvedValueOnce(
      jsonResponse(401, {
        detail: "That password is not correct.",
        auth_error: "invalid_password",
      })
    );
    fireEvent.change(screen.getByTestId("link-password"), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByTestId("link-confirm"));

    await waitFor(() =>
      expect(screen.getByTestId("link-error")).toHaveTextContent(
        AUTH_ERROR_MESSAGES.invalid_password
      )
    );
    // Still here, still able to try again, and definitely not signed in.
    expect(screen.getByTestId("location")).toHaveTextContent("/link-account");
    expect(screen.getByTestId("link-password")).toBeInTheDocument();
    expect(onAuth).not.toHaveBeenCalled();
  });

  test("clears the field between attempts", async () => {
    mockPending();
    renderPage();
    await waitForPrompt();

    fetch.mockResolvedValueOnce(
      jsonResponse(401, { detail: "no", auth_error: "invalid_password" })
    );
    fireEvent.change(screen.getByTestId("link-password"), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByTestId("link-confirm"));

    await waitFor(() => expect(screen.getByTestId("link-password")).toHaveValue(""));
  });
});

describe("a pending link that is gone", () => {
  test("an expired link on load returns to sign-in with the same code", async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse(400, { detail: "gone", auth_error: "link_expired" })
    );
    renderPage();

    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent(
        "/login?auth_error=link_expired"
      )
    );
  });

  test("an expired link on confirm returns to sign-in rather than retrying", async () => {
    mockPending();
    const onAuth = vi.fn();
    renderPage(onAuth);
    await waitForPrompt();

    fetch.mockResolvedValueOnce(
      jsonResponse(400, { detail: "gone", auth_error: "link_expired" })
    );
    fireEvent.change(screen.getByTestId("link-password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByTestId("link-confirm"));

    // Not retryable: the parked sign-in is spent, so there is nothing here to
    // try again against.
    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent(
        "/login?auth_error=link_expired"
      )
    );
    expect(onAuth).not.toHaveBeenCalled();
  });

  test("a network failure on load is treated as an expired link", async () => {
    fetch.mockRejectedValueOnce(new Error("offline"));
    renderPage();

    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent("auth_error=link_expired")
    );
  });
});

describe("cancelling", () => {
  test("tells the API to drop the pending link and goes home", async () => {
    mockPending();
    renderPage();
    await waitForPrompt();

    fetch.mockResolvedValueOnce(jsonResponse(200, { status: "cancelled" }));
    fireEvent.click(screen.getByTestId("link-cancel"));

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/"));
    expect(fetch.mock.calls[1][0]).toBe(`${API_BASE}/auth/link/cancel`);
  });

  test("leaves anyway if the cancel request fails", async () => {
    mockPending();
    renderPage();
    await waitForPrompt();

    fetch.mockRejectedValueOnce(new Error("offline"));
    fireEvent.click(screen.getByTestId("link-cancel"));

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/"));
  });
});

describe("submitting nothing", () => {
  test("an empty password sends no request", async () => {
    mockPending();
    renderPage();
    await waitForPrompt();

    fireEvent.click(screen.getByTestId("link-confirm"));

    // Only the pending lookup.
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});
