import { describe, it, expect, vi, beforeEach } from "vitest";
import { getVersions } from "../api/versionsApi"

global.fetch = vi.fn();

describe("getVersions API helper", () => {
    beforeEach(() => {
        fetch.mockReset();
    });

    it("GETs /api/verions/ without query params when no search is provided", async () => {
        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => [],
        });

        await getVersions("fake-token");

        const calledUrl = fetch.mock.calls[0][0].toString();
        expect(calledUrl).toMatch(/\/api\/versions\/$/)
    });

    it("GETs /api/verions/?serach=foo when search is provided", async () => {
        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => [],
        });

        await getVersions("fake-token", "foo");

        const calledUrl = fetch.mock.calls[0][0].toString();
        expect(calledUrl).toMatch(/\/api\/versions\/\?search=foo$/);
    });

    it("URL-encodes search strings with special characters", async () => {
        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => [],
        });

        await getVersions("fake-token", "hello world");

        const calledUrl = fetch.mock.calls[0][0].toString();
        expect(calledUrl).toContain("search=hello+world");
    });

    it("throws a user-friendly error when response is not ok", async () => {
        fetch.mockResolvedValueOnce({
            ok: false,
            status: 401,
            json: async () => ({ detail: "Not authenticated" }),
        });

        await expect(getVersions("bad-token")).rejects.toThrow("Not authenticated");
    });
});
