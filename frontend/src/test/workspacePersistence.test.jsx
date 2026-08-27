import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, test, expect, vi, beforeEach } from "vitest";

import App from "../App";
import Editor from "../pages/Editor";
import { WorkspaceProvider } from "../workspace";
import { STORAGE_KEY } from "../workspaceStorage";
import * as versionsApi from "../api/versionsApi";
import { validateKey } from "../api/client";
import * as authApi from "../api/authApi";

vi.mock("../api/versionsApi");
vi.mock("../api/authApi");
vi.mock("../api/templatesApi");
vi.mock("../api/exportApi");
vi.mock("../api/executeApi");
vi.mock("../api/client", () => ({ validateKey: vi.fn() }));

const USER = { email: "user@example.com" };

beforeEach(() => {
  vi.clearAllMocks();
  versionsApi.getVersions.mockResolvedValue([]);
  versionsApi.saveVersion.mockResolvedValue({ id: 1, name: "v1" });
});

function renderEditor() {
  return render(
    <MemoryRouter>
      <WorkspaceProvider>
        <Editor user={USER} />
      </WorkspaceProvider>
    </MemoryRouter>
  );
}

/**
 * A refresh, as far as this state is concerned: every React tree is destroyed
 * and a new provider mounts, so the only thing carried across is whatever
 * reached sessionStorage. Same as what the browser does on F5.
 */
function reload(view) {
  view.unmount();
  return renderEditor();
}

const promptBox = () => screen.getByLabelText(/your prompt/i);
const runButton = () => screen.getByRole("button", { name: /run prompt/i });
const pill = (model) => screen.getByRole("button", { name: model });

describe("workspace survives a refresh", () => {
  test("restores the draft prompt and the selected models", async () => {
    const view = renderEditor();

    fireEvent.change(promptBox(), { target: { value: "Explain quicksort" } });
    fireEvent.click(pill("gemini-2.5-pro"));
    await waitFor(() =>
      expect(pill("gemini-2.5-pro")).toHaveAttribute("aria-pressed", "true")
    );

    reload(view);

    expect(promptBox()).toHaveValue("Explain quicksort");
    expect(pill("gemini-2.5-pro")).toHaveAttribute("aria-pressed", "true");
    expect(pill("gpt-4o")).toHaveAttribute("aria-pressed", "true");
  });

  test("drops the API keys and makes the user validate again", async () => {
    validateKey.mockResolvedValue({ status: 200, data: { status: "valid" } });

    const view = renderEditor();

    fireEvent.change(promptBox(), { target: { value: "Explain quicksort" } });
    fireEvent.change(screen.getByLabelText("openai"), {
      target: { value: "sk-live-secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: /validate selected providers/i }));

    // Baseline: validating really does open the gate.
    await waitFor(() => expect(screen.getByText(/api key is valid/i)).toBeInTheDocument());
    await waitFor(() => expect(runButton()).toBeEnabled());

    reload(view);

    // The draft came back...
    expect(promptBox()).toHaveValue("Explain quicksort");
    // ...but nothing about the key did.
    expect(screen.getByLabelText("openai")).toHaveValue("");
    expect(screen.queryByText(/api key is valid/i)).not.toBeInTheDocument();
    expect(runButton()).toBeDisabled();
  });

  test("never writes a key or its validated status to storage", async () => {
    validateKey.mockResolvedValue({ status: 200, data: { status: "valid" } });

    renderEditor();

    fireEvent.change(promptBox(), { target: { value: "Explain quicksort" } });
    fireEvent.change(screen.getByLabelText("openai"), {
      target: { value: "sk-live-secret" },
    });
    fireEvent.change(screen.getByLabelText("anthropic"), {
      target: { value: "sk-ant-secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: /validate selected providers/i }));
    await waitFor(() => expect(screen.getByText(/api key is valid/i)).toBeInTheDocument());

    // Assert against the whole serialised payload, not a field list: a key
    // leaking under some future field name still has to show up in this string.
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    expect(raw).toContain("Explain quicksort");
    expect(raw).not.toContain("sk-live-secret");
    expect(raw).not.toContain("sk-ant-secret");

    const stored = JSON.parse(raw);
    expect(stored).not.toHaveProperty("apiKeys");
    expect(stored).not.toHaveProperty("isKeyValid");
  });

  test("restores the tab the user was on", async () => {
    const view = renderEditor();

    fireEvent.click(screen.getByRole("tab", { name: /versions/i }));
    await waitFor(() => expect(versionsApi.getVersions).toHaveBeenCalled());

    reload(view);

    expect(screen.getByRole("tab", { name: /versions/i })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByPlaceholderText("Version name")).toBeInTheDocument();
  });

  test("restores a half-typed version name and tag", async () => {
    const view = renderEditor();

    fireEvent.click(screen.getByRole("tab", { name: /versions/i }));
    await waitFor(() => expect(versionsApi.getVersions).toHaveBeenCalled());

    fireEvent.change(screen.getByPlaceholderText("Version name"), {
      target: { value: "quicksort-v2" },
    });
    fireEvent.change(screen.getByPlaceholderText("Tag (optional)"), {
      target: { value: "draft" },
    });

    reload(view);

    await waitFor(() =>
      expect(screen.getByPlaceholderText("Version name")).toHaveValue("quicksort-v2")
    );
    expect(screen.getByPlaceholderText("Tag (optional)")).toHaveValue("draft");
  });
});

describe("closing the tab clears the workspace", () => {
  test("a new tab starts from the first-time-visitor state", async () => {
    const view = renderEditor();

    fireEvent.change(promptBox(), { target: { value: "Explain quicksort" } });
    fireEvent.click(pill("gemini-2.5-pro"));
    fireEvent.click(screen.getByRole("tab", { name: /versions/i }));
    await waitFor(() => expect(versionsApi.getVersions).toHaveBeenCalled());
    fireEvent.change(screen.getByPlaceholderText("Version name"), {
      target: { value: "quicksort-v2" },
    });

    // What the browser does to sessionStorage when the tab closes: the next
    // tab gets its own, empty storage area.
    view.unmount();
    window.sessionStorage.clear();
    renderEditor();

    expect(screen.getByRole("tab", { name: /write/i })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(promptBox()).toHaveValue("");
    expect(pill("gpt-4o")).toHaveAttribute("aria-pressed", "true");
    expect(pill("gemini-2.5-pro")).toHaveAttribute("aria-pressed", "false");
    expect(runButton()).toBeDisabled();
  });

  test("signing out leaves nothing behind for the next user", async () => {
    // App owns the sign-out path, so this exercises the real handler rather
    // than reaching into the provider.
    authApi.getMe.mockResolvedValue({ email: "first@example.com" });
    authApi.logout.mockResolvedValue({});

    render(<App />);
    await screen.findByLabelText(/your prompt/i);

    fireEvent.change(promptBox(), { target: { value: "Explain quicksort" } });
    await waitFor(() =>
      expect(window.sessionStorage.getItem(STORAGE_KEY)).toContain("Explain quicksort")
    );

    fireEvent.click(await screen.findByRole("link", { name: /settings/i }));
    fireEvent.click(await screen.findByRole("button", { name: /log out/i }));

    await waitFor(() => expect(authApi.logout).toHaveBeenCalled());
    await waitFor(() =>
      expect(window.sessionStorage.getItem(STORAGE_KEY) ?? "").not.toContain(
        "Explain quicksort"
      )
    );
  });

  test("a corrupted payload is discarded rather than crashing the editor", () => {
    window.sessionStorage.setItem(STORAGE_KEY, "{not json");

    renderEditor();

    expect(promptBox()).toHaveValue("");
    expect(pill("gpt-4o")).toHaveAttribute("aria-pressed", "true");
    expect(window.sessionStorage.getItem(STORAGE_KEY)).not.toBe("{not json");
  });
});
