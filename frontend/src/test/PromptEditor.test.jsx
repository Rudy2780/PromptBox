import { describe, it, expect, vi, test } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import PromptEditor from "../components/PromptEditor";
import * as executeApi from "../api/executeApi";
import { useState } from "react";


function PromptEditorWrapper(props) {
  const [prompt, setPrompt] = useState("");
  return <PromptEditor {...props} prompt={prompt} setPrompt={setPrompt} />;
}

describe("PromptEditor", () => {
  it("calls executePrompt with the correct arguments and shows loading state", async () => {
    const executeSpy = vi
      .spyOn(executeApi, "executePrompt")
      .mockResolvedValue({
        model: "gpt-4o",
        response_text: "Hello!",
        latency: 0.5,
      });

    const handleResult = vi.fn();
    const handleError = vi.fn();

    render(
      <PromptEditorWrapper 
      model="gpt-4o"
      apiKey="sk-test"
      isKeyValid={true}
      onResult={handleResult}
      onError={handleError}
      />
    );

    const promptInput = screen.getByLabelText(/prompt/i);
    const submitButton = screen.getByRole("button", { name: /execute/i });

    fireEvent.change(promptInput, { target: { value: "Say hello" } });

    fireEvent.click(submitButton);

    expect(submitButton.disabled).toBe(true);

    await waitFor(() => {
      expect(executeSpy).toHaveBeenCalledWith({
        prompt: "Say hello",
        model: "gpt-4o",
        apiKey: "sk-test",
      });
    });

    expect(handleError).toHaveBeenCalledWith(null);
    expect(handleResult).toHaveBeenCalledWith({
      model: "gpt-4o",
      response_text: "Hello!",
      latency: 0.5,
    });

    expect(submitButton.disabled).toBe(false);
  });

  it("surfaces errors from executePrompt via onError", async () => {
    vi.spyOn(executeApi, "executePrompt").mockRejectedValue(
      new Error("Bad request")
    );

    const handleResult = vi.fn();
    const handleError = vi.fn();

    render(
      <PromptEditorWrapper 
      model="gpt-4o"
      apiKey="sk-test"
      isKeyValid={true}
      onResult={handleResult}
      onError={handleError}
      />
    );

    const promptInput = screen.getByLabelText(/prompt/i);
    const submitButton = screen.getByRole("button", { name: /execute/i });

    fireEvent.change(promptInput, { target: { value: "Say hello" } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(handleError).toHaveBeenCalledWith("Bad request");
    });

    expect(handleResult).not.toHaveBeenCalled();
  });
});

