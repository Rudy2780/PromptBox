import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import Login from "./Login";
import { MemoryRouter } from "react-router-dom";

describe("Login form validation", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    global.fetch = originalFetch;
  });

  it("prevents submission when email is empty", () => {
    render(<MemoryRouter><Login onAuth={vi.fn()} /></MemoryRouter>);

    fireEvent.change(screen.getByPlaceholderText(/Password/i), {
      target: { value: "password123" },
    });

    fireEvent.click(screen.getByTestId("signup-btn"));

    expect(global.fetch).not.toHaveBeenCalled();
    expect(screen.getByText(/Email is required/i)).toBeInTheDocument();
  });

  it("prevents submission when password is under 8 characters", () => {
    render(<MemoryRouter><Login onAuth={vi.fn()} /></MemoryRouter>);

    fireEvent.change(screen.getByPlaceholderText(/Email Id/i), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Password/i), {
      target: { value: "short" },
    });

    fireEvent.click(screen.getByTestId("signup-btn"));

    expect(global.fetch).not.toHaveBeenCalled();
    expect(
      screen.getByText(/Password must be at least 8 characters/i)
    ).toBeInTheDocument();
  });
});
