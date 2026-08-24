import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import PromptEditor from "../components/PromptEditor";
import * as executeApi from "../api/executeApi";
import { useState } from "react";


function PromptEditorWrapper(props) {
  const [prompt, setPrompt] = useState("");
  return <PromptEditor {...props} prompt={prompt} setPrompt={setPrompt} />;
}

describe("PromptEditor", () => {
  it("calls executeBatch with the correct arguments and shows loading state", async () => {
    const executeSpy = vi
      .spyOn(executeApi, "executeBatch")
      .mockResolvedValue([
        { model: "gpt-4o", response_text: "Hello!", latency: 0.5 },
      ]);

    const handleResult = vi.fn();
    const handleError = vi.fn();

    render(
      <PromptEditorWrapper
      models={["gpt-4o"]}
      apiKey={{ openai: "sk-test" }}
      isKeyValid={true}
      onResults={handleResult}
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
        models: ["gpt-4o"],
        apiKeys: { openai: "sk-test" },
      });
    });

    expect(handleError).toHaveBeenCalledWith(null);
    expect(handleResult).toHaveBeenCalledWith([
      { model: "gpt-4o", response_text: "Hello!", latency: 0.5 },
    ]);

    expect(submitButton.disabled).toBe(false);
  });

  it("surfaces errors from executeBatch via onError", async () => {
    vi.spyOn(executeApi, "executeBatch").mockRejectedValue(
      new Error("Bad request")
    );

    const handleResult = vi.fn();
    const handleError = vi.fn();

    render(
      <PromptEditorWrapper
      models={["gpt-4o"]}
      apiKey={{ openai: "sk-test" }}
      isKeyValid={true}
      onResults={handleResult}
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

