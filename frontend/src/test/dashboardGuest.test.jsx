import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import DashBoard from "../pages/dashboard";
import { GUEST_SESSION } from "../session";
import * as versionsApi from "../api/versionsApi";

vi.mock("../api/versionsApi");
vi.mock("../api/exportApi");
vi.mock("../api/executeApi");
vi.mock("../api/client");
vi.mock("../api/templatesApi", () => ({
  getTemplates: vi.fn().mockResolvedValue([]),
  getTemplate: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
  versionsApi.getVersions.mockResolvedValue([]);
});

describe("dashboard guest handling", () => {
  it("tells a guest why the authenticated panels are absent", async () => {
    render(<DashBoard user={GUEST_SESSION} onLogout={vi.fn()} />);

    expect(screen.getByTestId("guest-notice")).toBeInTheDocument();
    expect(screen.getByText(/browsing as guest/i)).toBeInTheDocument();
  });

  it("does not fire authenticated requests for a guest", async () => {
    render(<DashBoard user={GUEST_SESSION} onLogout={vi.fn()} />);

    // Previously the guest path rendered a dashboard whose panels silently
    // vanished; now they are deliberately not mounted, so no request is made
    // that could only 401.
    await waitFor(() => {
      expect(versionsApi.getVersions).not.toHaveBeenCalled();
    });
  });

  it("shows the signed-in user and loads their versions", async () => {
    render(<DashBoard user={{ email: "user@example.com" }} onLogout={vi.fn()} />);

    expect(screen.queryByTestId("guest-notice")).not.toBeInTheDocument();
    expect(screen.getByText(/signed in as user@example.com/i)).toBeInTheDocument();
    await waitFor(() => expect(versionsApi.getVersions).toHaveBeenCalled());
  });
});
