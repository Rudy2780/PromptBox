import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";

import Editor from "../pages/Editor";
import { WorkspaceProvider } from "../workspace";
import { GUEST_SESSION } from "../session";
import * as versionsApi from "../api/versionsApi";

vi.mock("../api/versionsApi");
vi.mock("../api/exportApi");
vi.mock("../api/executeApi");
vi.mock("../api/client");

beforeEach(() => {
  vi.clearAllMocks();
  versionsApi.getVersions.mockResolvedValue([]);
});

function renderEditor(user) {
  return render(
    <MemoryRouter>
      <WorkspaceProvider>
        <Editor user={user} />
      </WorkspaceProvider>
    </MemoryRouter>
  );
}

describe("editor guest handling", () => {
  it("tells a guest why the authenticated panels are absent", async () => {
    renderEditor(GUEST_SESSION);

    expect(screen.getByTestId("guest-notice")).toBeInTheDocument();
    expect(screen.getByText(/browsing as a guest/i)).toBeInTheDocument();
  });

  it("does not fire authenticated requests for a guest", async () => {
    renderEditor(GUEST_SESSION);

    // Previously the guest path rendered panels that silently vanished; the
    // version panels are not mounted at all, so no request is made that could
    // only 401.
    await waitFor(() => {
      expect(versionsApi.getVersions).not.toHaveBeenCalled();
    });
  });

  it("offers a guest no version panels on the Versions tab", async () => {
    renderEditor(GUEST_SESSION);

    screen.getByRole("tab", { name: /versions/i }).click();

    await waitFor(() => {
      expect(screen.getByText(/sign in to save and compare versions/i)).toBeInTheDocument();
    });
    expect(versionsApi.getVersions).not.toHaveBeenCalled();
  });

  it("loads versions for a signed-in user", async () => {
    renderEditor({ email: "user@example.com" });

    expect(screen.queryByTestId("guest-notice")).not.toBeInTheDocument();

    screen.getByRole("tab", { name: /versions/i }).click();

    await waitFor(() => expect(versionsApi.getVersions).toHaveBeenCalled());
  });
});
