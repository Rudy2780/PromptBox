import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, test, expect, vi, beforeEach } from "vitest";

import Login from "../components/Login";
import { oauthLoginUrl } from "../api/oauthApi";
import { API_BASE } from "../api/config";

/*
 * OAuth sign-in is a navigation, not a request. These assert on the anchor's
 * href rather than on a click handler, because the href IS the behaviour: an
 * OAuth login issued as fetch() would fail silently in a real browser -- it
 * cannot show a consent screen and cannot follow the cross-origin redirect
 * chain that ends with the session cookie being set.
 */

beforeEach(() => {
  global.fetch = vi.fn();
});

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login onAuth={vi.fn()} />
    </MemoryRouter>
  );
}

describe("oauthLoginUrl", () => {
  test("points at the API origin, not the SPA", () => {
    expect(oauthLoginUrl("google")).toBe(`${API_BASE}/auth/google/login`);
    expect(oauthLoginUrl("github")).toBe(`${API_BASE}/auth/github/login`);
  });
});

describe("provider sign-in links", () => {
  test("GitHub points at the GitHub login route", () => {
    renderLogin();
    expect(screen.getByTestId("github-btn")).toHaveAttribute(
      "href",
      `${API_BASE}/auth/github/login`
    );
  });

  test("Google points at the Google login route", () => {
    renderLogin();
    expect(screen.getByTestId("google-btn")).toHaveAttribute(
      "href",
      `${API_BASE}/auth/google/login`
    );
  });

  test("they are real links, so the browser navigates rather than fetching", () => {
    renderLogin();

    for (const id of ["github-btn", "google-btn"]) {
      const el = screen.getByTestId(id);
      expect(el.tagName).toBe("A");
      // A disabled-looking or href-less anchor is not focusable and does not
      // navigate; this is what the Phase 1 placeholder got wrong.
      expect(el.getAttribute("href")).toBeTruthy();
    }
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("no placeholder label survives", () => {
    renderLogin();
    expect(screen.queryByText(/coming soon/i)).not.toBeInTheDocument();
  });
});
