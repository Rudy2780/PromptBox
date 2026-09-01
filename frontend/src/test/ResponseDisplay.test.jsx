import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
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

  it("renders markdown as formatted elements", () => {
    render(
      <ResponseDisplay
        result={{
          model: "gemini-2.5-flash",
          response_text: "## Phase 1\n\n* **Why:** it is `python`\n",
          latency: 0.5,
        }}
      />
    );

    expect(screen.getByRole("heading", { name: "Phase 1" })).toBeTruthy();
    expect(screen.getByRole("listitem")).toBeTruthy();
    expect(screen.getByText("Why:").tagName).toBe("STRONG");
    expect(screen.getByText("python").tagName).toBe("CODE");
  });

  it("shows the raw markdown source when toggled", () => {
    const source = "## Phase 1\n";
    render(
      <ResponseDisplay
        result={{ model: "gpt-4o", response_text: source, latency: 0.5 }}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Markdown" }));

    expect(screen.queryByRole("heading", { name: "Phase 1" })).toBe(null);
    expect(screen.getByText(/## Phase 1/)).toBeTruthy();
  });
});
