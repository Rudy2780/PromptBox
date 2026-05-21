import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ResponseDisplay from "../components/ResponseDisplay";

describe("ResponseDisplay", () => {
  it("renders model name, response text, and latency", () => {
    render(
      <ResponseDisplay
        result={{ model: "gpt-4o", response_text: "Hello!", latency: 1.23 }}
      />
    );

    expect(screen.getByText(/gpt-4o/i)).toBeTruthy();
    expect(screen.getByText(/Hello!/i)).toBeTruthy();
    expect(screen.getByText(/1.23s/)).toBeTruthy();
  });

  it("renders nothing when no result is provided", () => {
    const { container } = render(<ResponseDisplay result={null} />);
    expect(container.firstChild).toBe(null);
  });
});

