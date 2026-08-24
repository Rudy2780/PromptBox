import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, test, expect, vi, beforeEach } from "vitest";
import { useState } from "react";

import ModelSelector from "../components/ModelSelector";
import { validateKey } from "../api/client";

vi.mock("../api/client", () => ({
  validateKey: vi.fn(),
}));

function ModelSelectorWrapper(props) {
  const [apiKey, setApiKey] = useState("");
  return <ModelSelector {...props} apiKey={apiKey} setApiKey={setApiKey} />;
}

const defaultProps = {
  provider: "openai",
  setProvider: vi.fn(),
  apiKey: "",
  setApiKey: vi.fn(),
  model: "gpt-4o",
  setModel: vi.fn(),
  onValidated: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("key validation when the request itself fails", () => {
  // A rejected fetch -- offline, CORS, or a Render free-tier cold-start timeout
  // -- used to skip setLoading(false), pinning the button at "Validating..."
  // forever. Since the button gates Execute, that bricked the app until reload.

  const clickValidate = () => {
    render(<ModelSelectorWrapper {...defaultProps} />);
    fireEvent.change(screen.getByPlaceholderText("Enter API Key"), {
      target: { value: "sk-test-key" },
    });
    fireEvent.click(screen.getByText("Validate Key"));
  };

  test("the button recovers instead of staying pinned at Validating...", async () => {
    validateKey.mockRejectedValue(new TypeError("Failed to fetch"));

    clickValidate();

    await waitFor(() => {
      expect(screen.getByText("Validate Key")).toBeInTheDocument();
    });
    expect(screen.queryByText(/validating/i)).not.toBeInTheDocument();
  });

  test("the user is told the server was unreachable", async () => {
    validateKey.mockRejectedValue(new TypeError("Failed to fetch"));

    clickValidate();

    await waitFor(() => {
      expect(screen.getByText(/could not reach the server/i)).toBeInTheDocument();
    });
  });

  test("a transport failure is not reported as an invalid key", async () => {
    validateKey.mockRejectedValue(new TypeError("Failed to fetch"));

    clickValidate();

    await waitFor(() => {
      expect(screen.getByText(/could not reach the server/i)).toBeInTheDocument();
    });
    expect(screen.queryByText("Invalid API key")).not.toBeInTheDocument();
  });

  test("execution stays gated after a failed validation", async () => {
    const onValidated = vi.fn();
    validateKey.mockRejectedValue(new TypeError("Failed to fetch"));

    render(<ModelSelectorWrapper {...defaultProps} onValidated={onValidated} />);
    fireEvent.change(screen.getByPlaceholderText("Enter API Key"), {
      target: { value: "sk-test-key" },
    });
    fireEvent.click(screen.getByText("Validate Key"));

    await waitFor(() => expect(onValidated).toHaveBeenCalledWith(false));
  });

  test("a retry after a failure can still succeed", async () => {
    validateKey.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    clickValidate();
    await waitFor(() =>
      expect(screen.getByText(/could not reach the server/i)).toBeInTheDocument()
    );

    // The button is usable again, so a transient failure is recoverable.
    validateKey.mockResolvedValue({ status: 200, data: { status: "valid" } });
    fireEvent.click(screen.getByText("Validate Key"));

    await waitFor(() => {
      expect(screen.getByText("API key is valid")).toBeInTheDocument();
    });
  });
});
