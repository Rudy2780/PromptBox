import { useEffect } from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, test, expect, vi, beforeEach } from "vitest";

import Community from "../pages/Community";
import { WorkspaceProvider } from "../workspace";
import { useWorkspace } from "../workspaceContext";
import * as templatesApi from "../api/templatesApi";

vi.mock("../api/templatesApi");

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

const TEMPLATES = [
  { id: 1, name: "Zero-Shot", category: "task", content: "[TASK INSTRUCTION]\n\nInput: [INPUT]\n\nOutput:" },
  { id: 2, name: "Steelman + Counter", category: "reasoning", content: "Argue the strongest case." },
  { id: 3, name: "Critique Mode", category: "structure", content: "Critique the following." },
];

/* Reads workspace state so tests can assert what a selection actually did. */
function PromptProbe() {
  const { prompt } = useWorkspace();
  return <div data-testid="prompt-value">{prompt}</div>;
}

/* Seeds the workspace with a draft prompt before the test interacts. */
function Seed({ value }) {
  const { setPrompt } = useWorkspace();
  useEffect(() => {
    if (value) setPrompt(value);
  }, [value, setPrompt]);
  return null;
}

function renderCommunity({ initialPrompt = "" } = {}) {
  return render(
    <MemoryRouter>
      <WorkspaceProvider>
        <Seed value={initialPrompt} />
        <Community />
        <PromptProbe />
      </WorkspaceProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  templatesApi.getTemplates.mockResolvedValue(TEMPLATES);
  vi.spyOn(window, "confirm").mockReturnValue(true);
});

describe("Community template catalogue", () => {
  test("renders the templates returned by the API", async () => {
    renderCommunity();
    await waitFor(() => {
      expect(screen.getByText("Zero-Shot")).toBeInTheDocument();
    });
    expect(screen.getByText("Steelman + Counter")).toBeInTheDocument();
    expect(screen.getByText("Critique Mode")).toBeInTheDocument();
  });

  test("filter pills are rendered", async () => {
    renderCommunity();
    await waitFor(() => expect(screen.getByText("Zero-Shot")).toBeInTheDocument());

    expect(screen.getByRole("button", { name: "All" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reasoning" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Structure" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Task" })).toBeInTheDocument();
  });

  test("choosing a filter refetches for that category", async () => {
    renderCommunity();
    await waitFor(() => expect(templatesApi.getTemplates).toHaveBeenCalledWith(null));

    fireEvent.click(screen.getByRole("button", { name: "Reasoning" }));

    await waitFor(() =>
      expect(templatesApi.getTemplates).toHaveBeenLastCalledWith("reasoning")
    );
  });

  test("clicking a template with an empty editor loads it directly", async () => {
    renderCommunity();
    await waitFor(() => expect(screen.getByText("Zero-Shot")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Zero-Shot"));

    expect(window.confirm).not.toHaveBeenCalled();
    expect(screen.getByTestId("prompt-value")).toHaveTextContent("[TASK INSTRUCTION]");
    expect(mockNavigate).toHaveBeenCalledWith("/editor");
  });

  test("clicking a template with existing content asks first", async () => {
    renderCommunity({ initialPrompt: "unsaved work" });
    await waitFor(() => expect(screen.getByText("Zero-Shot")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Zero-Shot"));

    expect(window.confirm).toHaveBeenCalled();
    expect(screen.getByTestId("prompt-value")).toHaveTextContent("[TASK INSTRUCTION]");
  });

  test("cancelling the confirmation keeps the existing content", async () => {
    window.confirm.mockReturnValue(false);
    renderCommunity({ initialPrompt: "unsaved work" });
    await waitFor(() => expect(screen.getByText("Zero-Shot")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Zero-Shot"));

    expect(window.confirm).toHaveBeenCalled();
    expect(screen.getByTestId("prompt-value")).toHaveTextContent("unsaved work");
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  test("surfaces a fetch failure", async () => {
    templatesApi.getTemplates.mockRejectedValue(new Error("Failed to fetch templates"));
    renderCommunity();

    await waitFor(() =>
      expect(screen.getByText("Failed to fetch templates")).toBeInTheDocument()
    );
  });

  test("shows an empty state when the catalogue is empty", async () => {
    templatesApi.getTemplates.mockResolvedValue([]);
    renderCommunity();

    await waitFor(() =>
      expect(screen.getByText("No templates found.")).toBeInTheDocument()
    );
  });

  test("shows only real catalogue data -- no author, likes or forks", async () => {
    renderCommunity();
    await waitFor(() => expect(screen.getByText("Zero-Shot")).toBeInTheDocument());

    // None of these exist in the backend, so none may appear in the UI.
    expect(screen.queryByPlaceholderText(/search/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/publish/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^@/)).not.toBeInTheDocument();
  });
});
