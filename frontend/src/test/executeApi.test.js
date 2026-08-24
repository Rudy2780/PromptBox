import { describe, it, expect, vi, beforeEach } from "vitest";
import { executePrompt } from "../api/executeApi";

global.fetch = vi.fn();

describe("executePrompt API helper", () => {
  beforeEach(() => {
    fetch.mockReset();
  });

  it("POSTs to /api/execute with correct payload", async () => {
    const mockResponse = {
      model: "gpt-4o",
      response_text: "Hello!",
      latency: 0.5,
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const result = await executePrompt({
      prompt: "Say hello",
      model: "gpt-4o",
      apiKey: "sk-test",
    });

    expect(fetch).toHaveBeenCalledWith(expect.stringMatching(/\/api\/execute$/), {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "PromptBox",
      },
      body: JSON.stringify({
        prompt: "Say hello",
        model: "gpt-4o",
        api_key: "sk-test",
      }),
    });

    expect(result).toEqual(mockResponse);
  });

  it("throws a user-friendly error when response is not ok", async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Prompt must not be empty." }),
    });

    await expect(
      executePrompt({
        prompt: "",
        model: "gpt-4o",
        apiKey: "",
      })
    ).rejects.toThrow("Prompt must not be empty.");
  });
});

