import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, test, expect, vi, beforeEach } from "vitest";

import Editor from "../pages/Editor";
import { WorkspaceProvider } from "../workspace";
import * as versionsApi from "../api/versionsApi";

vi.mock("../api/versionsApi");
vi.mock("../api/exportApi");
vi.mock("../api/executeApi");
vi.mock("../api/client");

beforeEach(() => {
  vi.clearAllMocks();
  versionsApi.getVersions.mockResolvedValue([]);
});

function renderEditor() {
  return render(
    <MemoryRouter>
      <WorkspaceProvider>
        <Editor user={{ email: "user@example.com" }} />
      </WorkspaceProvider>
    </MemoryRouter>
  );
}

describe("Editor tabs", () => {
  test("renders all three tabs with Write selected", () => {
    renderEditor();

    expect(screen.getByRole("tab", { name: /write/i })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByRole("tab", { name: /versions/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /results/i })).toBeInTheDocument();
  });

  test("the Write tab holds the prompt input and model pills", () => {
    renderEditor();

    expect(screen.getByLabelText(/your prompt/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run prompt/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "gpt-4o" })).toBeInTheDocument();
  });

  test("the selected model pill is marked pressed", () => {
    renderEditor();

    expect(screen.getByRole("button", { name: "gpt-4o" })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.getByRole("button", { name: "gpt-4o-mini" })).toHaveAttribute(
      "aria-pressed",
      "false"
    );
  });

  test("selecting a model pill toggles it", async () => {
    renderEditor();

    fireEvent.click(screen.getByRole("button", { name: "gemini-2.5-pro" }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "gemini-2.5-pro" })).toHaveAttribute(
        "aria-pressed",
        "true"
      )
    );
  });

  test("switching to Versions shows the version panels", async () => {
    renderEditor();

    fireEvent.click(screen.getByRole("tab", { name: /versions/i }));

    await waitFor(() => expect(versionsApi.getVersions).toHaveBeenCalled());
    expect(screen.getByPlaceholderText("Version name")).toBeInTheDocument();
  });

  test("Results is empty until a prompt has been run", () => {
    renderEditor();

    fireEvent.click(screen.getByRole("tab", { name: /results/i }));

    expect(screen.getByText(/no responses yet/i)).toBeInTheDocument();
  });

  test("no tags section without a tagged version loaded", () => {
    renderEditor();

    // PromptVersion.tag is the only tag data that exists, and nothing is
    // loaded yet -- so no TAGS block should be invented.
    expect(screen.queryByText("Tags")).not.toBeInTheDocument();
  });
});
