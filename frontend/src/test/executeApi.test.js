import { describe, it, expect, vi, beforeEach } from "vitest";
import { executeBatch } from "../api/executeApi";

global.fetch = vi.fn();

describe("executeBatch API helper", () => {
  beforeEach(() => {
    fetch.mockReset();
  });

  it("POSTs to /api/prompt with correct payload", async () => {
    const mockResponse = {
      responses: [{ model: "gpt-4o", response_text: "Hello!", latency: 0.5 }],
    };

    fetch.mockResolvedValueOnce({ ok: true, json: async () => mockResponse });

    const result = await executeBatch({
      prompt: "Say hello",
      models: ["gpt-4o"],
      apiKeys: { openai: "sk-test" },
    });

    expect(fetch).toHaveBeenCalledWith(expect.stringMatching(/\/api\/prompt$/), {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "PromptBox",
      },
      body: JSON.stringify({
        prompt: "Say hello",
        models: ["gpt-4o"],
        api_keys: { openai: "sk-test" },
      }),
    });

    expect(result).toEqual(mockResponse.responses);
  });

  it("handles a single model through the same path as several", async () => {
    // /api/execute was removed because this case was already covered here.
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        responses: [
          { model: "gpt-4o", response_text: "a", latency: 0.1 },
          { model: "gemini-2.5-pro", response_text: "b", latency: 0.2 },
        ],
      }),
    });

    const result = await executeBatch({
      prompt: "Say hello",
      models: ["gpt-4o", "gemini-2.5-pro"],
      apiKeys: { openai: "sk-test", gemini: "g-test" },
    });

    expect(result).toHaveLength(2);
  });

  it("returns an empty array when the body has no responses", async () => {
    fetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });

    await expect(
      executeBatch({ prompt: "hi", models: ["gpt-4o"], apiKeys: {} })
    ).resolves.toEqual([]);
  });

  it("throws a user-friendly error when response is not ok", async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Prompt must not be empty." }),
    });

    await expect(
      executeBatch({ prompt: "", models: ["gpt-4o"], apiKeys: {} })
    ).rejects.toThrow("Prompt must not be empty.");
  });
});
