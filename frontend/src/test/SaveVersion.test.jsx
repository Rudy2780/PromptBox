import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SaveVersion from "../components/SaveVersion";
import * as versionsApi from "../api/versionsApi";

vi.mock("../api/versionsApi");

describe("SaveVersion", () => {
    beforeEach(() => {
        vi.resetAllMocks();
    })

    it("displays confirmation message on success", async () => {
        versionsApi.saveVersion.mockResolvedValue({
            id: 1,
            name: "v1",
            prompt_text: "Explain quicksort",
            created_at: "2026-04-02T00:00:00",
        });

        render(
            <SaveVersion
            promptText="Explain quicksort"
            responseText={null}
            responseModel={null}
            responseLatency={null}
            />
        );

        fireEvent.change(screen.getByPlaceholderText("Version name"), {
            target: { value: "v1" },
        });
        fireEvent.change(screen.getByPlaceholderText("Tag (optional)"), {
            target: { value: "release-candidate" },
        });

        fireEvent.click(screen.getByRole("button", { name: /save version/i }));

        await waitFor(() => {
            expect(screen.getByText(/version saved/i)).toBeInTheDocument();
        });

        expect(versionsApi.saveVersion).toHaveBeenCalledWith({
            name: "v1",
            tag: "release-candidate",
            prompt_text: "Explain quicksort",
            response_text: null,
            response_model: null,
            response_latency: null,
        });
    });

    it("displays error message on failure", async () => {
        versionsApi.saveVersion.mockRejectedValue(
            new Error("Prompt text is required")
        );

        render(
            <SaveVersion
            promptText=""
            responseText={null}
            responseModel={null}
            responseLatency={null}
            />
        );

        fireEvent.change(screen.getByPlaceholderText("Version name"), {
            target: { value: "v1" },
        });

        fireEvent.click(screen.getByRole("button", { name: /save version/i }));

        await waitFor(() => {
            expect(screen.getByText(/prompt text is required/i)).toBeInTheDocument();
        });
    });
});
