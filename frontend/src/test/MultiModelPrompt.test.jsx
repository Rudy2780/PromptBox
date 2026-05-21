import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import React, { useState } from "react";
import PromptEditor from "../components/PromptEditor";
import ResponseDisplay from "../components/ResponseDisplay";

vi.mock("../api/executeApi", () => ({
  executeBatch: vi.fn(async () => [
    { model: "gpt-4o", response_text: "resp-openai", latency: 0.2 },
    { model: "gemini-2.5-flash", response_text: "resp-gemini", latency: 0.4 },
  ]),
}));

function Harness() {
  const [prompt, setPrompt] = useState("");
  const [results, setResults] = useState([]);
  return (
    <>
      <PromptEditor
        models={["gpt-4o", "gemini-2.5-flash"]}
        apiKey={{ openai: "ok", gemini: "gk" }}
        isKeyValid={true}
        onResults={setResults}
        onError={() => {}}
        prompt={prompt}
        setPrompt={setPrompt}
      />
      <ResponseDisplay results={results} />
    </>
  );
}

describe("Multi-model prompt execution", () => {
  it("submitting a prompt with two models renders two response windows", async () => {
    render(<Harness />);
    fireEvent.change(screen.getByLabelText(/Prompt/i), { target: { value: "Hello" } });
    fireEvent.click(screen.getByText(/Execute/i));

    await waitFor(() => {
      const cards = screen.getAllByText(/resp-/i);
      expect(cards).toHaveLength(2);
    });
  });

  it("each response window displays the correct model name", async () => {
    render(<Harness />);
    fireEvent.change(screen.getByLabelText(/Prompt/i), { target: { value: "Hello" } });
    fireEvent.click(screen.getByText(/Execute/i));

    await waitFor(() => {
      expect(screen.getByText("gpt-4o")).toBeInTheDocument();
      expect(screen.getByText("gemini-2.5-flash")).toBeInTheDocument();
    });
  });

  it("each response window displays response latency", async () => {
    render(<Harness />);
    fireEvent.change(screen.getByLabelText(/Prompt/i), { target: { value: "Hello" } });
    fireEvent.click(screen.getByText(/Execute/i));

    await waitFor(() => {
      // latencies formatted with toFixed(2)
      expect(screen.getAllByText(/0\.20s/i)).toHaveLength(1);
      expect(screen.getAllByText(/0\.40s/i)).toHaveLength(1);
    });
  });
});
