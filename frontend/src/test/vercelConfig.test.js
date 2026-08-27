import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, test, expect } from "vitest";

/**
 * vercel.json is what stops a refresh on /editor from returning Vercel's 404:
 * the static host has no file at that path, and only this rewrite tells it to
 * hand the request to index.html so React Router can resolve it client-side.
 *
 * It is deployment config, so nothing else in the app exercises it -- these
 * assertions are the only thing standing between a bad edit and a broken
 * refresh in production.
 */
// Relative to the Vite root, which is the frontend/ directory vitest runs in.
const config = JSON.parse(readFileSync(resolve(process.cwd(), "vercel.json"), "utf8"));

describe("vercel.json SPA rewrite", () => {
  test("sends unmatched paths to index.html", () => {
    expect(config.rewrites).toEqual([
      { source: "/(.*)", destination: "/index.html" },
    ]);
  });

  test("leaves static assets to the filesystem", () => {
    // Vercel resolves a request in a fixed order: redirects, then headers, then
    // the filesystem, and only then rewrites. Built assets exist as real files
    // (/assets/index-<hash>.js, /assets/index-<hash>.css, /vite.svg), so they
    // are served at the filesystem step and never reach the rewrite.
    //
    // That only holds while the rewrite stays a fallback. A `redirects` or
    // `routes` entry, or a rewrite whose source targets an asset path, would be
    // consulted first and could shadow a real file.
    expect(config.redirects).toBeUndefined();
    expect(config.routes).toBeUndefined();

    for (const rewrite of config.rewrites) {
      expect(rewrite.source).not.toMatch(/assets|\.js|\.css|\.svg/);
      expect(rewrite.destination).toBe("/index.html");
    }
  });
});
