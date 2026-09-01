import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, test, expect, vi, beforeEach } from "vitest";

import Login from "../components/Login";

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

describe("sign-in screen", () => {
  test("offers both OAuth providers", () => {
    renderLogin();
    expect(screen.getByTestId("github-btn")).toBeInTheDocument();
    expect(screen.getByTestId("google-btn")).toBeInTheDocument();
  });

  test("OAuth entry points are live, and the placeholder label is gone", () => {
    renderLogin();
    // They are links now rather than disabled buttons -- see
    // oauthLogin.test.jsx for where each one goes.
    expect(screen.getByTestId("github-btn")).toHaveAttribute("href");
    expect(screen.getByTestId("google-btn")).toHaveAttribute("href");
    expect(screen.queryByText("OAuth coming soon")).not.toBeInTheDocument();
  });

  test("the email form is hidden until the toggle is used", () => {
    renderLogin();

    expect(screen.queryByTestId("email-form")).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText("Email Id")).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("email-toggle"));

    expect(screen.getByTestId("email-form")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Email Id")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Password")).toBeInTheDocument();
  });

  test("the decorative Name field is gone", () => {
    renderLogin();
    fireEvent.click(screen.getByTestId("email-toggle"));

    // It was collected but never sent: there is no name column in the backend.
    expect(screen.queryByPlaceholderText("Name")).not.toBeInTheDocument();
  });

  test("guest access is still reachable", () => {
    renderLogin();
    expect(screen.getByTestId("guest-btn")).toBeInTheDocument();
    expect(screen.getByTestId("guest-btn")).not.toBeDisabled();
  });
});
