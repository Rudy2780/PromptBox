import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { describe, test, expect, vi, beforeEach } from "vitest";

import Login from "../components/Login";
import { AUTH_ERROR_MESSAGES, authErrorMessage } from "../oauthErrors";

/*
 * The API never sends prose for an OAuth failure -- it redirects to
 * /login?auth_error=<code> with an opaque slug, because that value ends up in
 * browser history and proxy logs. These cover the other half: turning the slug
 * into a sentence, and then getting it out of the URL.
 */

beforeEach(() => {
  global.fetch = vi.fn();
});

function LocationProbe() {
  const location = useLocation();
  return <span data-testid="location">{`${location.pathname}${location.search}`}</span>;
}

function renderAt(entry) {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route
          path="/login"
          element={
            <>
              <Login onAuth={vi.fn()} />
              <LocationProbe />
            </>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

describe("authErrorMessage", () => {
  test("has a sentence for every code the backend can send", () => {
    for (const code of [
      "access_denied",
      "invalid_state",
      "email_unverified",
      "provider_error",
      "provider_unavailable",
      "link_expired",
      "invalid_password",
    ]) {
      expect(AUTH_ERROR_MESSAGES[code]).toBeTruthy();
      expect(authErrorMessage(code)).toBe(AUTH_ERROR_MESSAGES[code]);
    }
  });

  test("never echoes an unrecognised code back into the page", () => {
    // The parameter is attacker-controllable -- anyone can send a link with
    // ?auth_error=<anything> in it -- so it must not be rendered verbatim.
    const injected = "<script>alert(1)</script>";
    expect(authErrorMessage(injected)).not.toContain(injected);
    expect(authErrorMessage("totally-made-up")).toBeTruthy();
  });

  test("no error means no message", () => {
    expect(authErrorMessage(null)).toBeNull();
    expect(authErrorMessage(undefined)).toBeNull();
    expect(authErrorMessage("")).toBeNull();
  });
});

describe("the login screen reading ?auth_error", () => {
  test("shows the plain-language message for the code", async () => {
    renderAt("/login?auth_error=email_unverified");

    await waitFor(() =>
      expect(
        screen.getByText(AUTH_ERROR_MESSAGES.email_unverified)
      ).toBeInTheDocument()
    );
  });

  test("clears the parameter from the URL once shown", async () => {
    renderAt("/login?auth_error=access_denied");

    await waitFor(() =>
      expect(screen.getByText(AUTH_ERROR_MESSAGES.access_denied)).toBeInTheDocument()
    );
    // A refresh or a shared link must not replay a failure that is over.
    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent("/login")
    );
    expect(screen.getByTestId("location").textContent).not.toContain("auth_error");
  });

  test("keeps any other query parameters", async () => {
    renderAt("/login?auth_error=access_denied&next=%2Feditor");

    await waitFor(() =>
      expect(screen.getByTestId("location").textContent).not.toContain("auth_error")
    );
    expect(screen.getByTestId("location").textContent).toContain("next=%2Feditor");
  });

  test("an unknown code still produces a readable message", async () => {
    renderAt("/login?auth_error=who-knows");

    await waitFor(() =>
      expect(screen.getByText(authErrorMessage("who-knows"))).toBeInTheDocument()
    );
  });

  test("a clean login screen shows no error", () => {
    renderAt("/login");
    expect(screen.queryByText(AUTH_ERROR_MESSAGES.access_denied)).not.toBeInTheDocument();
  });

  test("showing an error attempts no request", async () => {
    renderAt("/login?auth_error=provider_error");
    await waitFor(() =>
      expect(screen.getByText(AUTH_ERROR_MESSAGES.provider_error)).toBeInTheDocument()
    );
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
