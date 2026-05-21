import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ErrorMessage from "../components/ErrorMessage";

describe("ErrorMessage", () => {
  it("renders the error message when provided", () => {
    render(<ErrorMessage message="Something went wrong" />);

    expect(screen.getByText(/something went wrong/i)).toBeTruthy();
  });

  it("renders nothing when no error message is provided", () => {
    const { container } = render(<ErrorMessage message={null} />);
    expect(container.firstChild).toBe(null);
  });
});

