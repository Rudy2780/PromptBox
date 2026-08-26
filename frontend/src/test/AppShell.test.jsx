import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, test, expect } from "vitest";

import AppShell from "../components/AppShell";
import { displayNameFor, initialsFor } from "../identity";

function renderShell(user, route = "/editor") {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AppShell user={user}>
        <p>content</p>
      </AppShell>
    </MemoryRouter>
  );
}

describe("AppShell sidebar", () => {
  test("renders both nav groups and all destinations", () => {
    renderShell({ email: "rudy@example.com" });

    expect(screen.getByText("Workspace")).toBeInTheDocument();
    expect(screen.getByText("Discover")).toBeInTheDocument();

    for (const label of ["Editor", "Chains", "Cost forecast", "Community", "Settings"]) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
  });

  test("marks the current route active", () => {
    renderShell({ email: "rudy@example.com" }, "/community");

    expect(screen.getByRole("link", { name: "Community" }).className).toContain(
      "is-active"
    );
    expect(screen.getByRole("link", { name: "Editor" }).className).not.toContain(
      "is-active"
    );
  });

  test("renders the children it wraps", () => {
    renderShell({ email: "rudy@example.com" });
    expect(screen.getByText("content")).toBeInTheDocument();
  });

  test("shows plan caption for a signed-in user", () => {
    renderShell({ email: "rudy@example.com" });
    expect(screen.getByText("Free plan")).toBeInTheDocument();
  });

  test("a guest is not described as having a plan", () => {
    renderShell({ isGuest: true });
    expect(screen.getByText("Not signed in")).toBeInTheDocument();
    expect(screen.queryByText("Free plan")).not.toBeInTheDocument();
  });
});

describe("identity derived from the email", () => {
  // The backend stores no name column, so the local part is all there is.
  test.each([
    [{ email: "rudy.rutiaga@example.com" }, "Rudy Rutiaga", "RR"],
    [{ email: "priya@example.com" }, "Priya", "PR"],
    [{ email: "alex_dev@example.com" }, "Alex Dev", "AD"],
    [{ isGuest: true }, "Guest", "GU"],
  ])("%o -> %s / %s", (user, name, initials) => {
    expect(displayNameFor(user)).toBe(name);
    expect(initialsFor(user)).toBe(initials);
  });
});
