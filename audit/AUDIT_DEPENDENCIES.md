# PromptBox — Dependency Audit

**Date:** 2026-08-24
**Scope:** `frontend/` (React 19 + Vite, npm) and `backend/` (FastAPI, pip)
**Mode:** REPORT ONLY — no fix, upgrade, or install command was run. No manifest or lockfile was modified.

**Tooling actually used (and not used):**

| Tool | Status | Notes |
|---|---|---|
| `npm audit` / `npm audit --json` | ✅ ran | npm 10.9.3, Node v22.20.0 |
| `npm outdated` | ✅ ran | |
| `npm ls <pkg> --all` | ✅ ran | for dependency paths |
| `pip-audit` | ❌ **not installed** | `pip-audit: command not found` — not installed per constraint |
| `safety` | ❌ **not installed** | `safety: command not found` — not installed per constraint |
| OSV.dev API (`api.osv.dev/v1/querybatch` + `/v1/vulns/{id}`) | ✅ ran | Read-only HTTP. Used as the pip-audit substitute — OSV is the same advisory database pip-audit queries. All 64 pinned packages queried by exact version. |
| PyPI JSON API (`pypi.org/pypi/{pkg}/json`) | ✅ ran | Read-only, for latest-version / release-date / EOL data |

Every advisory ID, version range, and fix version below is quoted from real tool output. Nothing is inferred from memory.

---

## 1. Summary counts by severity

### Frontend (`npm audit` metadata block, verbatim)

```json
"vulnerabilities": { "info": 0, "low": 2, "moderate": 0, "high": 10, "critical": 1, "total": 13 },
"dependencies": { "prod": 8, "dev": 292, "optional": 52, "peer": 8, "peerOptional": 0, "total": 299 }
```

`13 vulnerabilities (2 low, 10 high, 1 critical)` — counted by **package**, at the max severity of the advisories affecting it. 43 individual advisories underlie those 13 packages.

| | Count |
|---|---|
| Critical | 1 (`vitest`) |
| High | 10 |
| Low | 2 |
| **Total vulnerable packages** | **13** |
| Of which **direct** (in `package.json`) | 3 — `vitest`, `vite`, `react-router-dom` |
| Of which **transitive** | 10 |
| Of which **dev-only (never shipped to users)** | **12 of 13** |
| Of which **runtime (shipped in the bundle)** | **1** — `react-router` via `react-router-dom` |

### Backend (OSV.dev, 64 pinned packages queried by exact version)

| | Count |
|---|---|
| Packages queried | 64 |
| Packages with ≥1 advisory | **11** |
| Distinct advisories (deduped by CVE alias) | **25** |
| High | 13 |
| Moderate | 8 |
| Low | 3 |
| Severity not assigned by OSV | 1 (`click`, PYSEC-only record) |
| Advisories with **no fix available at all** | **1** — `ecdsa` CVE-2024-23342 (Minerva) |

### Combined headline

- **1 critical** (frontend, `vitest`, dev-only, requires a listening Vitest UI server).
- **23 high** total (10 frontend packages + 13 backend advisories).
- **The single most user-facing item is `react-router-dom` 7.13.1** — the only vulnerable frontend package that ships to browsers, carrying 12 advisories including a CVSS 8.1 RCE-class deserialization issue.
- **The single most server-facing items are `starlette` 0.52.1, `urllib3` 2.6.3, and `pyasn1` 0.6.2** — all runtime, all in the request path.

---

## 2. Frontend

### 2.1 `package.json` as declared

```json
"dependencies":    { "react": "^19.2.0", "react-dom": "^19.2.0", "react-router-dom": "^7.13.1" }
"devDependencies": { "@eslint/js": "^9.39.1", "@testing-library/jest-dom": "^6.9.1",
                     "@testing-library/react": "^16.3.2", "@types/react": "^19.2.7",
                     "@types/react-dom": "^19.2.3", "@vitejs/plugin-react": "^5.1.1",
                     "eslint": "^9.39.1", "eslint-plugin-react-hooks": "^7.0.1",
                     "eslint-plugin-react-refresh": "^0.4.24", "globals": "^16.5.0",
                     "jsdom": "^28.1.0", "vite": "^7.3.1", "vitest": "^4.0.18" }
```

Only three runtime dependencies. Everything else is build/lint/test tooling.

### 2.2 The single most important frontend finding

**`npm audit --json` reports `"fixAvailable": true` (boolean) for all 13 vulnerable packages.**

npm emits a boolean `true` only when the fix requires **no semver-major change to any direct dependency**. When a major bump is needed, npm emits an *object* (`{"name":…,"version":…,"isSemVerMajor":true}`) and the human output says `fix available via npm audit fix --force`. Neither appears anywhere in this report — the output ends with plain:

```
To address all issues, run:
  npm audit fix
```

I verified this independently against the lockfile's parent semver ranges — every required fix version already falls inside the range its parent declares:

| Vulnerable pkg | Parent → declared range | Installed | Fix needs | Inside range? |
|---|---|---|---|---|
| `vite` | root `^7.3.1` | 7.3.1 | > 7.3.4 (`npm outdated` Wanted: **7.3.6**) | ✅ minor |
| `vitest` | root `^4.0.18` | 4.0.18 | ≥ 4.1.0 (Wanted: **4.1.11**) | ✅ minor |
| `react-router-dom` | root `^7.13.1` | 7.13.1 | ≥ 7.18.2 (Wanted: **7.18.2**) | ✅ minor |
| `react-router` | `react-router-dom` → `7.13.1` (exact) | 7.13.1 | 7.18.2 | ✅ moves with its parent |
| `undici` | `jsdom@28.1.0` → `^7.21.0` | 7.22.0 | ≥ 7.29.0 | ✅ |
| `postcss` | `vite@7.3.1` → `^8.5.6` | 8.5.8 | > 8.5.22 | ✅ |
| `nanoid` | `postcss@8.5.8` → `^3.3.11` | 3.3.11 | ≥ 3.3.18 | ✅ |
| `esbuild` | `vite@7.3.1` → `^0.27.0` | 0.27.3 | ≥ 0.28.1 | ✅ |
| `picomatch` | `vite@7.3.1` → `^4.0.3` | 4.0.3 | ≥ 4.0.4 | ✅ |
| `js-yaml` | `@eslint/eslintrc@3.3.4` → `^4.1.1` | 4.1.1 | ≥ 4.3.1 | ✅ |
| `flatted` | `flat-cache@4.0.1` → `^3.2.9` | 3.3.4 | > 3.4.1 | ✅ |
| `brace-expansion` | `minimatch@3.1.5` → `^1.1.7` | 1.1.12 | ≥ 1.1.18 | ✅ |
| `@babel/core` | `@vitejs/plugin-react@5.1.4` → `^7.29.0` | 7.29.0 | > 7.29.0 | ✅ |

**Conclusion: no major version bump of any direct dependency is required to clear all 13 advisories, including the critical one.** The `vite` 7 → 8 and `eslint` 9 → 10 majors visible in `npm outdated` are *available* but **not required for security**. That materially lowers the risk of remediation here.

### 2.3 Findings — DIRECT dependencies

---

#### F-1 · `vitest` — 🔴 **CRITICAL** · DIRECT · **DEV-ONLY**

- **Installed:** 4.0.18 · **Declared:** `^4.0.18` (devDependencies)
- **Path:** `frontend@0.0.0 → vitest@4.0.18` (top-level)
- **Advisory:** [GHSA-5xrq-8626-4rwp](https://github.com/advisories/GHSA-5xrq-8626-4rwp) — *"When Vitest UI server is listening, arbitrary file can be read and executed"*
- **CWE:** CWE-22 (Path Traversal), CWE-862 (Missing Authorization) · **CVSS 9.8**
- **Vulnerable range:** `>=4.0.0 <4.1.0` — installed 4.0.18 is in range
- **Fix:** ≥ 4.1.0; `npm outdated` Wanted = **4.1.11**
- **Breaking risk: NONE.** 4.1.11 satisfies the existing `^4.0.18`. Same major.
- **Priority context:** This is the only Critical, but it is **dev-only and conditionally exploitable** — it requires the Vitest **UI** server (`vitest --ui`) to be listening. This repo's scripts are `"test": "vitest run"` and `"test:watch": "vitest"` — **neither enables the UI**, and `@vitest/ui` is not installed. Real-world exposure here is therefore near zero. Still worth fixing, because it is free.
- **Test after:** `npm test` (19 test files under `src/test/` + `src/components/Login.test.jsx`).

---

#### F-2 · `react-router-dom` / `react-router` — 🔴 **HIGH** · DIRECT · **RUNTIME (shipped to users)**

- **Installed:** `react-router-dom@7.13.1` → `react-router@7.13.1` · **Declared:** `^7.13.1` (dependencies)
- **Path:** `frontend@0.0.0 → react-router-dom@7.13.1 → react-router@7.13.1`. `react-router-dom` is flagged `isDirect: true`; `react-router` is transitive but pinned **exactly** by its parent, so it only moves when `react-router-dom` moves.
- **This is the ONLY vulnerable frontend package that ships in the production bundle.** All 12 others are dev tooling. **Treat this as the top frontend priority despite `vitest` carrying the higher label.**
- **Fix:** 7.18.2; `npm outdated` Wanted = **7.18.2**
- **Breaking risk: NONE→MINOR.** 7.18.2 satisfies `^7.13.1`. Same major, five minors of drift.

**All 12 advisories, with the installed 7.13.1 checked against each range:**

| Sev | Advisory | Title | Vulnerable range | Hits 7.13.1? | CWE | CVSS |
|---|---|---|---|---|---|---|
| High | [GHSA-49rj-9fvp-4h2h](https://github.com/advisories/GHSA-49rj-9fvp-4h2h) | vendored turbo-stream v2 arbitrary constructor invocation via TYPE_ERROR deserialization → unauth RCE | `>=7.0.0 <=7.14.1` | ✅ | CWE-502 | **8.1** |
| High | [GHSA-8646-j5j9-6r62](https://github.com/advisories/GHSA-8646-j5j9-6r62) | XSS in unstable RSC redirect handling via `javascript:` targets | `>=7.7.0 <7.13.2` | ✅ | CWE-79 | 8.0 |
| Moderate | [GHSA-f22v-gfqf-p8f3](https://github.com/advisories/GHSA-f22v-gfqf-p8f3) | Stored XSS via unescaped Location header in prerendered redirect HTML | `>=7.5.1 <7.13.2` | ✅ | CWE-79 | 5.4 |
| High | [GHSA-8x6r-g9mw-2r78](https://github.com/advisories/GHSA-8x6r-g9mw-2r78) | DoS via unbounded path expansion in `__manifest` endpoint | `>=7.0.0 <7.15.0` | ✅ | CWE-400 | 7.5 |
| High | [GHSA-rxv8-25v2-qmq8](https://github.com/advisories/GHSA-rxv8-25v2-qmq8) | DoS via reflected user input in single-fetch | `>=7.0.0 <7.14.0` | ✅ | CWE-770 | 7.5 |
| Low | [GHSA-84g9-w2xq-vcv6](https://github.com/advisories/GHSA-84g9-w2xq-vcv6) | Potential CSRF via PUT/PATCH/DELETE document requests | `>=7.12.0 <7.15.1` | ✅ | CWE-352 | 3.1 |
| Moderate | [GHSA-wrjc-x8rr-h8h6](https://github.com/advisories/GHSA-wrjc-x8rr-h8h6) | Open redirect via backslash in `<Link>` / `useNavigate` (CVE-2025-68470 bypass) | `>=6.0.0 <7.18.0` | ✅ | CWE-601 | n/a |
| Moderate | [GHSA-h8fp-f39c-q6mh](https://github.com/advisories/GHSA-h8fp-f39c-q6mh) | RSCErrorHandler missing protocol validation (XSS) | `>=7.11.0 <7.18.0` | ✅ | CWE-79 | 6.9 |
| Moderate | [GHSA-337j-9hxr-rhxg](https://github.com/advisories/GHSA-337j-9hxr-rhxg) | Arbitrary constructor injection via `deserializeErrors()` in SSR hydration | `>=6.4.0 <7.18.0` | ✅ | CWE-470 | 6.1 |
| High | [GHSA-chx6-hx7r-mcp5](https://github.com/advisories/GHSA-chx6-hx7r-mcp5) | Unauthenticated DoS via inefficient route matching | `>=7.0.0 <7.18.0` | ✅ | CWE-400/407 | n/a |
| Moderate | [GHSA-2j2x-hqr9-3h42](https://github.com/advisories/GHSA-2j2x-hqr9-3h42) | Same-origin redirect with path starting `//` → open redirect via protocol-relative URL | `>=7.0.0 <7.14.1` | ✅ | CWE-601 | n/a |
| High | [GHSA-qwww-vcr4-c8h2](https://github.com/advisories/GHSA-qwww-vcr4-c8h2) | RSC mode CSRF bypass — action executes before 400 response | `>=7.12.0 <7.18.2` | ✅ | CWE-352 | n/a |

**Exposure note:** PromptBox is a client-side SPA — `src/main.jsx` mounts into the browser and `src/api/client.js` talks to `https://promptbox-9d83.onrender.com` over `fetch`. There is **no React Router SSR, RSC, prerender, or single-fetch server** in this repo. That means the SSR/RSC-specific advisories (49rj, 8646, f22v, rxv8, 337j, qwww, 8x6r) are **not reachable in the current deployment**. The ones that **are** reachable client-side are the open-redirect pair — **GHSA-wrjc-x8rr-h8h6** (backslash in `<Link>`/`useNavigate`) and **GHSA-2j2x-hqr9-3h42** (`//` protocol-relative) — plus **GHSA-chx6-hx7r-mcp5** (route-matching DoS). This tempers severity but does not remove it: any future move to SSR/prerender re-arms the whole set.

- **Test after:** navigation across `/`, login → `pages/dashboard.jsx`; `src/test/App.test.jsx`, `login.test.jsx`, `register.test.jsx`.

---

#### F-3 · `vite` — 🔴 **HIGH** · DIRECT · **DEV-ONLY**

- **Installed:** 7.3.1 · **Declared:** `^7.3.1` (devDependencies)
- **Path:** top-level, and deduped under `@vitejs/plugin-react@5.1.4` and `vitest@4.0.18`
- **Fix:** > 7.3.4; `npm outdated` Wanted = **7.3.6**
- **Breaking risk: NONE.** 7.3.6 satisfies `^7.3.1`. **A Vite 7 → 8 major is NOT required.** `vite.config.js` is 8 lines (`plugins: [react()]` plus an inline `test:` block) — even a hypothetical v8 bump would have little config surface to break, but it is not on the table for security.

| Sev | Advisory | Title | Range | Hits 7.3.1? | CVSS |
|---|---|---|---|---|---|
| Moderate | [GHSA-4w7w-66w2-5vf9](https://github.com/advisories/GHSA-4w7w-66w2-5vf9) | Path traversal in optimized-deps `.map` handling | `>=7.0.0 <=7.3.1` | ✅ | n/a |
| High | [GHSA-v2wj-q39q-566r](https://github.com/advisories/GHSA-v2wj-q39q-566r) | `server.fs.deny` bypassed with queries | `>=7.1.0 <=7.3.1` | ✅ | n/a |
| High | [GHSA-p9ff-h696-f583](https://github.com/advisories/GHSA-p9ff-h696-f583) | Arbitrary file read via dev-server WebSocket | `>=7.0.0 <=7.3.1` | ✅ | n/a |
| Moderate | [GHSA-v6wh-96g9-6wx3](https://github.com/advisories/GHSA-v6wh-96g9-6wx3) | `launch-editor`: NTLMv2 hash disclosure via UNC paths (**Windows only**) | `>=7.0.0 <=7.3.4` | ✅ | n/a |
| High | [GHSA-fx2h-pf6j-xcff](https://github.com/advisories/GHSA-fx2h-pf6j-xcff) | `server.fs.deny` bypass on Windows alternate paths (**Windows only**) | `>=7.0.0 <=7.3.4` | ✅ | 7.5 |

**Exposure note:** All five require the **dev server** to be running, and two are Windows-only (dev host here is darwin 24.5.0). `vite build` output is unaffected. Real risk applies to a developer running `npm run dev` on an untrusted network.

- **Test after:** `npm run dev` (HMR loads), `npm run build`, `npm run preview`.

### 2.4 Findings — TRANSITIVE dependencies (all **DEV-ONLY**)

None of these ten packages appear in `package.json`; none reach the production bundle. Each parent path is from `npm ls <pkg> --all`.

| # | Package | Installed | Sev | Pulled in by (verbatim `npm ls` path) | Advisories | Fix needed |
|---|---|---|---|---|---|---|
| F-4 | `undici` | 7.22.0 | High | `frontend → jsdom@28.1.0 → undici@7.22.0` | **16** (see below) | ≥ 7.29.0 (in `jsdom`'s `^7.21.0`) |
| F-5 | `postcss` | 8.5.8 | High | `frontend → vite@7.3.1 → postcss@8.5.8` | 4 | > 8.5.22 |
| F-6 | `js-yaml` | 4.1.1 | High | `frontend → eslint@9.39.3 → @eslint/eslintrc@3.3.4 → js-yaml@4.1.1` | 3 | ≥ 4.3.1 |
| F-7 | `brace-expansion` | 1.1.12 | High | `frontend → eslint@9.39.3 → minimatch@3.1.5 → brace-expansion@1.1.12` | 4 | ≥ 1.1.18 |
| F-8 | `flatted` | 3.3.4 | High | `frontend → eslint@9.39.3 → file-entry-cache@8.0.0 → flat-cache@4.0.1 → flatted@3.3.4` | 2 | > 3.4.1 |
| F-9 | `nanoid` | 3.3.11 | High | `frontend → vite@7.3.1 → postcss@8.5.8 → nanoid@3.3.11` | 2 | ≥ 3.3.18 |
| F-10 | `picomatch` | 4.0.3 | High | `frontend → vite@7.3.1 → picomatch@4.0.3` (also via `fdir`, `tinyglobby`, and `vitest@4.0.18`) | 2 | ≥ 4.0.4 |
| F-11 | `esbuild` | 0.27.3 | Low | `frontend → vite@7.3.1 → esbuild@0.27.3` | 1 | ≥ 0.28.1 |
| F-12 | `@babel/core` | 7.29.0 | Low | `frontend → @vitejs/plugin-react@5.1.4 → @babel/core@7.29.0` (also via `eslint-plugin-react-hooks@7.0.1`) | 1 | > 7.29.0 |

**Detail on the notable ones:**

**F-4 `undici` 7.22.0 — 16 advisories** (highest count in the tree). All reached only through `jsdom`, i.e. only inside the Vitest DOM test environment (`vite.config.js` → `test.environment: 'jsdom'`). Highs affecting 7.22.0: [GHSA-f269-vfmq-vjvj](https://github.com/advisories/GHSA-f269-vfmq-vjvj) (WebSocket 64-bit length overflow crash, 7.5, `<7.24.0`), [GHSA-vrm6-8vpv-qv8q](https://github.com/advisories/GHSA-vrm6-8vpv-qv8q) (permessage-deflate unbounded memory, 7.5, `<7.24.0`), [GHSA-v9p9-hfj2-hcw8](https://github.com/advisories/GHSA-v9p9-hfj2-hcw8) (unhandled exception on `server_max_window_bits`, 7.5, `<7.24.0`), [GHSA-vxpw-j846-p89q](https://github.com/advisories/GHSA-vxpw-j846-p89q) (WS fragment-count DoS, 7.5, `<7.28.0`), [GHSA-4cwx-7wf7-3272](https://github.com/advisories/GHSA-4cwx-7wf7-3272) (cross-user info disclosure + parse crash via degenerate private cache directives, 7.4, `<7.29.0`). Plus 9 moderate (request smuggling [GHSA-2mjp-6q6p-2qxm], CRLF injection [GHSA-4992-7rv2-5pvq], [GHSA-m8rv-5g2x-5cg5], Set-Cookie percent-decode header injection [GHSA-p88m-4jfj-68fv], cache whitespace bypasses [GHSA-pr7r-676h-xcf6], [GHSA-jr45-8vmc-qm54], retry desync [GHSA-8xcm-r25x-g524], cookie attribute injection [GHSA-v3r7-h72x-cjcm], dedup handler memory [GHSA-phc3-fgpg-7m6h]) and 2 low ([GHSA-g8m3-5g58-fq7m], [GHSA-35p6-xmwp-9g52]). **Exposure: test-runner only. Not shipped, not on any production request path.**

**F-5 `postcss` 8.5.8** — the highest-severity items are [GHSA-6g55-p6wh-862q](https://github.com/advisories/GHSA-6g55-p6wh-862q) (arbitrary file read via attacker-controlled `sourceMappingURL`, CVSS 7.5, `<=8.5.11`) and [GHSA-r28c-9q8g-f849](https://github.com/advisories/GHSA-r28c-9q8g-f849) (path traversal in previous-source-map auto-loading, 7.5, `<=8.5.17`), plus [GHSA-qx2v-qp2m-jg93](https://github.com/advisories/GHSA-qx2v-qp2m-jg93) (XSS via unescaped `</style>` in stringify output, 6.1, `<8.5.10`) and [GHSA-fxqj-rqcc-2cmp](https://github.com/advisories/GHSA-fxqj-rqcc-2cmp) (`<=8.5.22`). These matter at **build time**, when PostCSS processes CSS — the project ships hand-written CSS only (`App.css`, `index.css`, six component CSS files), no third-party CSS pulled in, so attacker-controlled `sourceMappingURL` is not a realistic vector here.

**F-11 `esbuild` 0.27.3** — [GHSA-g7r4-m6w7-qqqr](https://github.com/advisories/GHSA-g7r4-m6w7-qqqr), arbitrary file read via the dev server, **Windows only**, CVSS 2.5. Not applicable on this darwin host.

**F-12 `@babel/core` 7.29.0** — [GHSA-4x5r-pxfx-6jf8](https://github.com/advisories/GHSA-4x5r-pxfx-6jf8), arbitrary file read via `sourceMappingURL` comment, CVSS 3.2, local + high complexity.

### 2.5 `npm outdated` — drift analysis

Verbatim output:

```
Package                      Current   Wanted   Latest
@eslint/js                    9.39.3   9.39.5   10.0.1
@testing-library/jest-dom      6.9.1    6.9.1    7.0.1
@types/react                 19.2.14  19.2.18  19.2.18
@types/react-dom              19.2.3   19.2.5   19.2.5
@vitejs/plugin-react           5.1.4    5.2.0    6.1.0
eslint                        9.39.3   9.39.5   10.9.0
eslint-plugin-react-hooks      7.0.1    7.1.1    7.1.1
eslint-plugin-react-refresh   0.4.26   0.4.26    0.5.4
globals                       16.5.0   16.5.0   17.11.0
jsdom                         28.1.0   28.1.0   29.1.1
react                         19.2.4   19.2.8   19.2.8
react-dom                     19.2.4   19.2.8   19.2.8
react-router-dom              7.13.1   7.18.2   7.18.2
vite                           7.3.1    7.3.6    8.2.2
vitest                        4.0.18   4.1.11   4.1.11
```

**Group A — patch/minor, inside existing `^` ranges. SAFE. Clears every advisory.**

| Package | Current → Wanted | Runtime? | Security-relevant |
|---|---|---|---|
| `react-router-dom` | 7.13.1 → 7.18.2 | **RUNTIME** | ✅ clears all 12 react-router advisories |
| `vite` | 7.3.1 → 7.3.6 | dev | ✅ clears vite + postcss + nanoid + esbuild + picomatch |
| `vitest` | 4.0.18 → 4.1.11 | dev | ✅ clears the Critical |
| `eslint` | 9.39.3 → 9.39.5 | dev | ✅ clears js-yaml + brace-expansion + flatted |
| `@eslint/js` | 9.39.3 → 9.39.5 | dev | — |
| `react` / `react-dom` | 19.2.4 → 19.2.8 | **RUNTIME** | no advisory; 4 patches behind |
| `@types/react` | 19.2.14 → 19.2.18 | dev | — |
| `@types/react-dom` | 19.2.3 → 19.2.5 | dev | — |
| `@vitejs/plugin-react` | 5.1.4 → 5.2.0 | dev | ✅ carries the `@babel/core` fix |
| `eslint-plugin-react-hooks` | 7.0.1 → 7.1.1 | dev | — |

**Group B — MAJOR available, NOT required for security. Do not bundle these with the fix.**

| Package | Current → Latest | Dev/Runtime | What could concretely break |
|---|---|---|---|
| `vite` | 7.3.1 → **8.2.2** | dev | Flat-config/plugin-API changes in a Vite major; `vite.config.js` is minimal (`plugins:[react()]` + an inline `test:` block), so surface is small — but the inline `test:` block is a **Vitest** config living in the Vite config, and a Vite 8 + Vitest 4.1 pairing must be validated together. Also forces a `@vitejs/plugin-react` 6 bump for peer compatibility. **Skip — 7.3.6 already fixes everything.** |
| `eslint` + `@eslint/js` | 9.39.3 → **10.x** | dev | ESLint 10 drops/changes flat-config surface. `eslint.config.js` imports `defineConfig`/`globalIgnores` from `eslint/config`, and spreads `js.configs.recommended`, `reactHooks.configs.flat.recommended`, `reactRefresh.configs.vite` — all three plugin config shapes must be v10-compatible simultaneously. Also needs `globals` 17. **Lint-only; zero security benefit. Defer.** |
| `jsdom` | 28.1.0 → **29.1.1** | dev | This is the only path to a fully-clean `undici`. But a jsdom major changes DOM/API emulation and can break `@testing-library/react` assertions across all 19 test files. **`npm audit` says the `undici` fix is reachable without it** (`^7.21.0` admits 7.29.x), so jsdom 29 is optional. |
| `@testing-library/jest-dom` | 6.9.1 → **7.0.1** | dev | Matcher behavior changes (`toBeInTheDocument`, `toHaveTextContent`, etc.). `src/test/setup.js` is a bare `import '@testing-library/jest-dom'`, so it applies globally — a v7 matcher change would surface as assertion failures across the whole suite. No security driver. **Defer.** |
| `@vitejs/plugin-react` | 5.1.4 → **6.1.0** | dev | Peer-locked to Vite 8. Only relevant if you take Vite 8. |
| `globals` | 16.5.0 → **17.11.0** | dev | Only consumed as `globals.browser` in `eslint.config.js`. Low risk, but no benefit. |
| `eslint-plugin-react-refresh` | 0.4.26 → **0.5.4** | dev | Pre-1.0 minor = breaking by convention. `reactRefresh.configs.vite` export could move. |

**Nothing in Group B is required to reach zero advisories.**

---

## 3. Backend

### 3.1 How dependencies are pinned

`backend/requirements.txt` contains **64 entries, 100% pinned with exact `==`.** No ranges, no `>=`, no unpinned bare names, no `--hash` entries, no comments, no sections.

```
annotated-doc==0.0.4
annotated-types==0.7.0
anthropic==0.84.0
...
websockets==16.0
```

**Assessment — this is a `pip freeze` dump, not a curated manifest.** Evidence:

1. It is strict-alphabetical (case-insensitive) with mixed original casing (`Pygments`, `SQLAlchemy`, `docstring_parser`, `pyasn1_modules`) — the exact shape `pip freeze` emits.
2. It lists **transitive** packages as if they were first-class: `annotated-types`, `pydantic_core`, `httpcore`, `h11`, `sniffio`, `pycparser`, `googleapis-common-protos`, `proto-plus`, `uritemplate`, `six`, `iniconfig`, `pluggy`. Only ~13 of the 64 are things this project actually chose.

**Consequences, both directions:**

- ✅ **Good:** builds are fully reproducible by version (though not by hash), and there is no floating-range drift.
- ❌ **Bad — the significant finding:** because *transitives are pinned too*, **upgrading a direct dependency does not upgrade its dependencies.** `starlette==0.52.1` will stay at 0.52.1 even if you bump `fastapi`, because the pin overrides what FastAPI would have resolved. **This file has to be regenerated wholesale, not patched line-by-line** — otherwise you silently hold vulnerable transitives back. This is exactly the situation with `starlette`, `urllib3`, `pyasn1`, `idna`, `cryptography`, and `httplib2` below.

**No lockfile.** There is no `requirements.lock`, no `poetry.lock`, no `Pipfile.lock`, no `pyproject.toml`, no `uv.lock`, and no hash pinning (`--require-hashes`). `requirements.txt` is doing double duty as manifest and lock, which is why the two roles are in conflict.

### 3.2 Installed versions / environment

**There is no virtualenv.** `ls -d .venv venv env` returns nothing; `backend/.gitignore` contains only `*.db`.

Deps are installed into the **user's system-wide Python 3.13.7** (`/Library/Frameworks/Python.framework/Versions/3.13/`), which holds **193 packages** — PromptBox's 64 plus unrelated ones (`jupyter`, `jupyterlab`, `streamlit`, `Flask`, `flask-cors`, `Flask-Mail`, `Flask-PyMongo`, `pandas`, `matplotlib`, `scikit-image`, `basketball_reference_web_scraper`, …).

**Verification result:** all 64 pinned packages are installed, and **all 64 match their pin exactly** — 0 missing, 0 version mismatches. So the audit below reflects what is actually running.

> ⚠️ **Caveat on reverse-dependency data:** because this is a shared global environment, the reverse-dep map picks up non-PromptBox parents. Where a parent below is `streamlit`, `flask`, `jupyter-server`, or `basketball-reference-web-scraper`, that is **not** a PromptBox edge and is excluded from the direct/transitive calls. In a clean venv, `uvicorn` and `click` would have no parent (uvicorn is a project-direct runtime, per `README.md` line 133: `uvicorn app.main:app --reload --port 8000`).

### 3.3 Direct vs transitive (backend)

**DIRECT — imported in `app/` or `tests/`, or invoked as tooling:**

| Package | Pinned | Evidence |
|---|---|---|
| `fastapi` | 0.135.1 | `app/main.py`, all `app/api/routes_*.py` |
| `uvicorn` | 0.41.0 | `README.md:133` run command |
| `SQLAlchemy` | 2.0.48 | `app/database.py`, `app/main.py`, `app/models/*` |
| `pydantic` | 2.12.5 | `app/schemas/*` |
| `python-jose` | 3.5.0 | `app/dependencies/auth.py:3`, `app/services/auth_service.py:5`, `tests/test_auth.py:81` |
| `bcrypt` | 5.0.0 | `app/utils/security.py:1` (used **directly**, not through passlib) |
| `python-dotenv` | 1.2.2 | `app/config.py:2` |
| `openai` | 2.26.0 | `app/providers/openai_provider.py`, `app/services/llm_service.py` |
| `anthropic` | 0.84.0 | `app/providers/anthropic_provider.py`, `app/services/llm_service.py` |
| `google-genai` | 1.66.0 | `app/providers/gemini_provider.py:7`, `app/services/llm_service.py:16` (`from google import genai`) |
| `pytest` | 9.0.2 | 11 test modules — **dev-only** |
| `pytest-asyncio` | 1.3.0 | **dev-only** (see hygiene H-7) |
| `email-validator` | 2.3.0 | pinned top-level; used by Pydantic `EmailStr` |
| `httpx` | 0.28.1 | required by `fastapi.testclient` — **dev-only in this app**, also a dep of the three SDKs |

**TRANSITIVE** (pinned but never imported by PromptBox): `starlette` (← fastapi), `anyio`/`sniffio`/`h11`/`httpcore` (← httpx/uvicorn/starlette), `ecdsa`/`rsa`/`pyasn1` (← python-jose), `pyasn1_modules` (← google-auth), `cryptography` (← google-auth), `certifi`/`idna`/`charset-normalizer`/`urllib3` (← requests/httpx), `requests` (← google-api-core, google-genai), `httplib2`/`uritemplate`/`pyparsing` (← google-api-python-client), `click` (← uvicorn), `Pygments`/`iniconfig`/`pluggy` (← pytest), `protobuf`/`grpcio`/`grpcio-status`/`proto-plus`/`googleapis-common-protos` (← google-*), `annotated-types`/`pydantic_core`/`typing_extensions`/`typing-inspection`/`annotated-doc` (← pydantic/fastapi), `six` (← ecdsa), `tqdm`/`jiter`/`distro`/`docstring_parser` (← openai/anthropic), `tenacity`/`websockets` (← google-genai), `dnspython` (← email-validator), `cffi`/`pycparser` (← cryptography), `google-auth`/`google-api-core`/`google-auth-httplib2` (← google-*).

**Pinned but neither imported nor pulled in by any PromptBox package:** `passlib`, `google-generativeai`, `google-ai-generativelanguage`, `google-api-python-client` — see §5 hygiene.

### 3.4 Findings — backend advisories (OSV.dev, per exact pinned version)

---

#### B-1 · `starlette` 0.52.1 — 🔴 **HIGH** · TRANSITIVE (← `fastapi`) but **explicitly pinned** · **RUNTIME**

Sits directly in the HTTP request path of every PromptBox endpoint. **5 advisories.**

| Sev | Advisory / CVE | Title | Fixed in |
|---|---|---|---|
| **HIGH** | [GHSA-82w8-qh3p-5jfq](https://github.com/advisories/GHSA-82w8-qh3p-5jfq) / CVE-2026-54283 · CVSS 7.5 | `request.form()` limits silently ignored for `application/x-www-form-urlencoded` → DoS | **1.3.1** |
| **HIGH** | [GHSA-wqp7-x3pw-xc5r](https://github.com/advisories/GHSA-wqp7-x3pw-xc5r) / CVE-2026-48818 · CVSS 7.5 | SSRF + NTLM credential theft via UNC paths in `StaticFiles` on Windows | **1.1.0** |
| Moderate | [GHSA-86qp-5c8j-p5mr](https://github.com/advisories/GHSA-86qp-5c8j-p5mr) / CVE-2026-48710 · CVSS 5.4 | Missing Host header validation poisons `request.url.path`, bypassing path-based security checks | **1.0.1** |
| Moderate | [GHSA-x746-7m8f-x49c](https://github.com/advisories/GHSA-x746-7m8f-x49c) / CVE-2026-48817 · CVSS 5.3 | Arbitrary HTTP method dispatched to `HTTPEndpoint` attributes via `getattr` | **1.1.0** |
| Low | [GHSA-jp82-jpqv-5vv3](https://github.com/advisories/GHSA-jp82-jpqv-5vv3) / CVE-2026-54282 · CVSS 3.1 | Unvalidated request path concatenated into authority poisons `request.url.hostname` | **1.3.0** |

**Reachability, checked against the source** (`grep -rn "HTTPEndpoint\|request.form\|StaticFiles\|TrustedHost" app tests` → **NONE FOUND**):
- CVE-2026-48818 (`StaticFiles`) — **not reachable**, no StaticFiles mount, and the deploy target is Linux (Render).
- CVE-2026-48817 (`HTTPEndpoint`) — **not reachable**, the app uses decorator routes via `APIRouter`, no class-based endpoints.
- CVE-2026-54283 (`request.form()`) — **not directly reachable** today; no route calls `request.form()` and no `Form(...)`/`UploadFile` params exist. Becomes live the moment a form endpoint is added.
- CVE-2026-48710 (Host header) / CVE-2026-54282 — **partially relevant.** `app/main.py` adds no `TrustedHostMiddleware`, so Host is unvalidated; there are currently no path-based security checks to poison, so impact is limited to any future proxy/redirect logic.

**⚠️ Fix path is a MAJOR jump: 0.52.1 → 1.3.1+ (latest 1.6.0).** Starlette 1.0.0 shipped 2026-03-22; the pinned 0.52.1 predates it (2026-01-18). The good news: `fastapi==0.135.1`'s own metadata declares `starlette>=0.46.0` **with no upper bound**, so pip will *accept* starlette 1.x against the currently pinned FastAPI. The risk is that FastAPI 0.135.1 (Jan 2026) was released **before** Starlette 1.0 existed and was never tested against it.

**Recommended: bump `fastapi` 0.135.1 → 0.141.1 (2026-07-29, post-Starlette-1.x) and `starlette` 0.52.1 → 1.6.0 together as one change.** Do not move starlette alone.

---

#### B-2 · `pyasn1` 0.6.2 — 🔴 **HIGH ×4** · TRANSITIVE (← `python-jose`, `rsa`, `pyasn1_modules`←`google-auth`) · **RUNTIME**

All four are unauthenticated DoS in the ASN.1 decoder. `python-jose` is on the JWT auth path (`app/dependencies/auth.py`), and `google-auth` is on the Gemini path — so this decoder is reachable from request handling.

| Sev | Advisory / CVE | Title | Fixed in |
|---|---|---|---|
| HIGH | [GHSA-jr27-m4p2-rc6r](https://github.com/advisories/GHSA-jr27-m4p2-rc6r) / CVE-2026-30922 · CVSS 7.5 | DoS via unbounded recursion | **0.6.3** |
| HIGH | [GHSA-8ppf-4f7h-5ppj](https://github.com/advisories/GHSA-8ppf-4f7h-5ppj) / CVE-2026-59885 · CVSS 7.5 | Quadratic complexity in OBJECT IDENTIFIER / RELATIVE-OID processing | **0.6.4** |
| HIGH | [GHSA-hm4w-wwcw-mr6r](https://github.com/advisories/GHSA-hm4w-wwcw-mr6r) / CVE-2026-59886 · CVSS 7.5 | Uncontrolled resource consumption converting decoded REAL values | **0.6.4** |
| HIGH | [GHSA-m4p7-r5rc-7g4j](https://github.com/advisories/GHSA-m4p7-r5rc-7g4j) / CVE-2026-59884 · CVSS 7.5 | BER/CER/DER decoder DoS via unbounded long-form tag IDs | **0.6.4** |

**Fix: 0.6.2 → 0.6.4 (latest, 2026-07-09). Patch-level. Breaking risk: NONE.** This is the highest-value, lowest-risk backend change available.

---

#### B-3 · `urllib3` 2.6.3 — 🔴 **HIGH ×2** · TRANSITIVE (← `requests` ← `google-api-core`, `google-genai`) · **RUNTIME**

| Sev | Advisory / CVE | Title | Fixed in |
|---|---|---|---|
| HIGH | [GHSA-mf9v-mfxr-j63j](https://github.com/advisories/GHSA-mf9v-mfxr-j63j) / CVE-2026-44432 · CVSS 7.5 | Decompression-bomb safeguards bypassed in parts of the streaming API | **2.7.0** |
| HIGH | [GHSA-qccp-gfcp-xxvc](https://github.com/advisories/GHSA-qccp-gfcp-xxvc) / CVE-2026-44431 · CVSS 7.5 | Sensitive headers forwarded across origins in proxied low-level redirects | **2.7.0** |

**Exposure:** CVE-2026-44431 is the concerning one — PromptBox forwards **user-supplied LLM provider API keys** to third-party endpoints. Cross-origin header leakage on redirect is a credential-disclosure path for exactly that data. Mitigating factor: the OpenAI and Anthropic SDKs use `httpx` (not urllib3); the urllib3 path is reached via `requests` inside `google-api-core`/`google-genai`.

**Fix: 2.6.3 → 2.7.0 (latest, 2026-05-07). Minor. Breaking risk: NONE→MINOR.**

---

#### B-4 · `cryptography` 46.0.5 — 🔴 **HIGH ×3, Moderate ×2, Low ×1** · TRANSITIVE (← `google-auth`) · **RUNTIME**

| Sev | Advisory / CVE | Title | Fixed in |
|---|---|---|---|
| **HIGH** | [GHSA-537c-gmf6-5ccf](https://github.com/advisories/GHSA-537c-gmf6-5ccf) · CVSS 7.5 | **Vulnerable OpenSSL included in cryptography wheels** | **48.0.1** |
| **HIGH** | [GHSA-g6cj-pr64-35w5](https://github.com/advisories/GHSA-g6cj-pr64-35w5) / CVE-2026-69247 | PKCS#7 EnvelopedData decryption exposes a Bleichenbacher oracle | **50.0.0** |
| **HIGH** | [GHSA-jwv3-5hgf-82ww](https://github.com/advisories/GHSA-jwv3-5hgf-82ww) / CVE-2026-69249 | Duplicate self-signed intermediates cause exponential path-building | **49.0.0** |
| Moderate | [GHSA-m2h6-j472-rp4c](https://github.com/advisories/GHSA-m2h6-j472-rp4c) / CVE-2026-69248 | Verifier accepts wildcard DNS names, allowing escape from `permittedSubtrees` | **49.0.0** |
| Moderate | [GHSA-p423-j2cm-9vmq](https://github.com/advisories/GHSA-p423-j2cm-9vmq) / CVE-2026-39892 | Buffer overflow if non-contiguous buffers passed to APIs | **46.0.7** |
| Low | [GHSA-m959-cc7f-wv43](https://github.com/advisories/GHSA-m959-cc7f-wv43) / CVE-2026-34073 | Incomplete DNS name-constraint enforcement on peer names | **46.0.6** |

**Two-tier fix. This is the one place where clearing everything demands a big major jump:**
- **46.0.5 → 46.0.7** clears the two lowest (39892, 34073). **Patch-level, zero risk.**
- Clearing **GHSA-537c** (bundled-OpenSSL, HIGH) needs **≥ 48.0.1**; clearing all six needs **50.0.0** (latest, 2026-07-31). That is a **4-major jump (46 → 50)**. `cryptography` majors routinely remove deprecated APIs and raise the minimum Rust/OpenSSL toolchain.
- **Mitigating:** PromptBox does not import `cryptography` anywhere. It arrives only via `google-auth`, which uses it for JWT/certificate signing. **PKCS#7 EnvelopedData (69247) and path-building (69249) are not exercised by this app.** GHSA-537c (bundled OpenSSL) is the one that matters, since it affects the TLS stack regardless of which APIs you call.
- **Recommendation:** take 46.0.7 immediately (free), and schedule 50.0.0 as a separate, tested change.

---

#### B-5 · `ecdsa` 0.19.1 — 🔴 **HIGH, ⚠️ NO FIX AVAILABLE** · TRANSITIVE (← `python-jose`) · **RUNTIME**

| Sev | Advisory / CVE | Title | Fixed in |
|---|---|---|---|
| **HIGH** | [GHSA-wj6h-64fc-37mp](https://github.com/advisories/GHSA-wj6h-64fc-37mp) / **CVE-2024-23342** · CVSS 7.4 (`AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:N`) | **Minerva timing attack on P-256 in python-ecdsa** | **OSV lists NO fixed version. The latest release (0.19.2, 2026-03-26) does not fix it.** |
| Moderate | [GHSA-9f5j-8jwj-x28g](https://github.com/advisories/GHSA-9f5j-8jwj-x28g) / CVE-2026-33936 | DoS via improper DER length validation in crafted private keys | **0.19.2** |

**This is the only advisory in either ecosystem with no upgrade path.** The `python-ecdsa` maintainers have stated the pure-Python implementation cannot be made side-channel resistant; the project carries no fix and none is planned. Upgrading to 0.19.2 clears CVE-2026-33936 but **leaves CVE-2024-23342 permanently open.**

**Reachability assessment — this is where it lands well for PromptBox:** Minerva is a timing attack on **ECDSA signing with P-256**. This app's JWT usage is **HMAC-SHA256 only**:

```python
# app/services/auth_service.py:25
return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
# app/dependencies/auth.py:19
payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
```

`algorithms=["HS256"]` is explicitly pinned on decode (good — this also closes the algorithm-confusion class that hit python-jose historically). **No ECDSA key operation is ever performed**, so CVE-2024-23342 is **not reachable in current code**. `ecdsa` is dead weight dragged in by `python-jose`'s unconditional `ecdsa!=0.15` requirement.

**Strategic note:** `python-jose` 3.5.0 is itself the **latest release, and it is from 2025-05-28** — 15 months stale as of this audit, with no OSV advisories against 3.5.0 (the older CVE-2024-33663 algorithm-confusion and CVE-2024-33664 JWE-DoS were fixed in 3.4.0, so 3.5.0 is clean). Still, a JWT library that has not shipped in over a year, and that hard-depends on a package with a permanently unfixed HIGH CVE, is a **long-term supply-chain liability**. Given this app uses HS256 only, migrating to **PyJWT** (already installed in this environment) would drop `ecdsa`, `rsa`, and `pyasn1` from the tree entirely and eliminate B-2 and B-5 at once. Recorded as a strategic recommendation, not an urgent fix.

---

#### B-6 · `httplib2` 0.31.2 — 🔴 **HIGH** · TRANSITIVE (← `google-api-python-client`, `google-auth-httplib2`) · **RUNTIME (but see hygiene)**

- [GHSA-j5g9-f88f-gfj3](https://github.com/advisories/GHSA-j5g9-f88f-gfj3) / CVE-2026-59939 · CVSS 7.5 — *Decompression Bomb DoS via unbounded gzip/deflate response handling*
- **Fixed in: 0.32.0** (latest, 2026-06-26). 0.31.2 → 0.32.0, minor. **Breaking risk: NONE.**
- **Better fix:** `httplib2` is reached **only** through `google-api-python-client` ← `google-generativeai`, which is **the legacy Gemini SDK that PromptBox does not use** (the code imports `from google import genai`, the *new* `google-genai`). Removing `google-generativeai` deletes `httplib2`, `google-api-python-client`, `google-auth-httplib2`, `google-ai-generativelanguage`, `uritemplate`, and `pyparsing` from the tree — and this advisory with them. See H-4.

---

#### B-7 · `requests` 2.32.5 — 🟡 Moderate · TRANSITIVE (← `google-api-core`, `google-genai`) · runtime

- [GHSA-gc5v-m9x4-r6x2](https://github.com/advisories/GHSA-gc5v-m9x4-r6x2) / CVE-2026-25645 · CVSS 5.5 (`AV:L/AC:H/PR:L/UI:R/S:U/C:N/I:H/A:N`) — *Insecure temp file reuse in `extract_zipped_paths()`*
- **Fixed in: 2.33.0** (latest 2.34.2). **Breaking risk: NONE→MINOR.**
- **Exposure: very low.** Local attack vector, and `extract_zipped_paths()` is a niche utility PromptBox never calls (`requests` is not imported anywhere in `app/` or `tests/`).

---

#### B-8 · `idna` 3.11 — 🟡 Moderate · TRANSITIVE (← `httpx`, `anyio`, `requests`, `email-validator`) · **RUNTIME**

- [GHSA-65pc-fj4g-8rjx](https://github.com/advisories/GHSA-65pc-fj4g-8rjx) / CVE-2026-45409 — *Specially crafted inputs to `idna.encode()` can bypass the CVE-2024-3651 fix* (DoS)
- **Fixed in: 3.15** (latest 3.19, 2026-08-18). **Breaking risk: NONE.**
- **Exposure:** reachable via `email-validator`, which Pydantic's `EmailStr` uses on the registration path — user-controlled email domains flow into IDNA encoding. Worth taking.

---

#### B-9 · `pytest` 9.0.2 — 🟡 Moderate · DIRECT · **DEV-ONLY**

- [GHSA-6w46-j5rx-g56g](https://github.com/advisories/GHSA-6w46-j5rx-g56g) / CVE-2025-71176 · CVSS 5.5 — *Vulnerable tmpdir handling*
- **Fixed in: 9.0.3** (latest 9.1.1). **Patch. Breaking risk: NONE.**
- **DEV-ONLY — never deployed.** Local privilege/symlink-class issue on shared machines. Low priority.

---

#### B-10 · `Pygments` 2.19.2 — 🟢 Low · TRANSITIVE (← `pytest`) · **DEV-ONLY**

- [GHSA-5239-wwwm-4pmq](https://github.com/advisories/GHSA-5239-wwwm-4pmq) / CVE-2026-4539 · CVSS 3.3 — *ReDoS via inefficient GUID-matching regex*
- **Fixed in: 2.20.0** (latest 2.21.0). **Breaking risk: NONE.**
- **DEV-ONLY** — arrives via `pytest`'s output formatting. Lowest priority backend item.

---

#### B-11 · `click` 8.3.1 — ⚪ severity not assigned by OSV · TRANSITIVE (← `uvicorn`) · runtime tooling

- **PYSEC-2026-2132 / CVE-2026-7246** — OSV returns **no summary and no `database_specific.severity`** for this record (PYSEC-only, no GHSA counterpart). CVSS vector as published: `CVSS:3.1/AV:L/AC:H/PR:H/UI:R/S:C/C:H/I:H/A:H`.
- **Fixed in: 8.3.3** (latest 8.4.2). **Breaking risk: NONE.**
- **Exposure: minimal.** The vector is Local / High complexity / High privileges required / User interaction required — an attacker already needs privileged local access. `click` is only present as `uvicorn`'s CLI parser. I am deliberately not assigning a severity label OSV did not provide.

### 3.5 Backend EOL / staleness (not vulnerabilities, but risk)

| Package | Pinned | Latest (date) | Assessment |
|---|---|---|---|
| `passlib` | 1.7.4 | **1.7.4 — released 2020-10-08** | **~6 years without a release. Effectively abandoned.** See H-1 — it is also *empirically broken* in this environment. |
| `google-generativeai` | 0.8.6 | 0.8.6 (2025-12-16) | **Google's deprecated legacy Gemini SDK**, superseded by `google-genai`. Both are pinned; only `google-genai` is used. See H-4. |
| `python-jose` | 3.5.0 | **3.5.0 — released 2025-05-28** | Latest, but 15 months stale. No advisories against 3.5.0. Liability via `ecdsa` (B-5). |
| `starlette` | 0.52.1 | 1.6.0 (2026-08-08) | **A full major behind.** 5 advisories (B-1). |
| `cryptography` | 46.0.5 | 50.0.0 (2026-07-31) | **4 majors behind.** 6 advisories (B-4). |
| `openai` | 2.26.0 | **3.3.1** (2026-08-19) | **A full major behind.** No advisories. Deliberate upgrade needed. |
| `anthropic` | 0.84.0 | **1.0.0** (2026-08-20) | **Pre-1.0 → 1.0 stable.** No advisories. Deliberate upgrade needed. |
| `google-genai` | 1.66.0 | **2.19.0** (2026-08-19) | **A full major behind.** No advisories. |
| `protobuf` | 5.29.6 | 7.36.0 | Two majors behind; pinned by `google-ai-generativelanguage`. No advisories. |
| `grpcio` | 1.78.0 / `grpcio-status` 1.71.2 | 1.83.0 | **Version skew:** `grpcio` 1.78.0 vs `grpcio-status` 1.71.2 — 7 minors apart. These normally ship in lockstep. Suspicious pin, worth checking. |
| `fastapi` | 0.135.1 | 0.141.1 | 6 minors behind. No direct advisories, but needed alongside the starlette fix. |
| `uvicorn` | 0.41.0 | 0.52.4 | 11 minors behind. No advisories. |
| `pydantic` | 2.12.5 | 2.13.4 | 1 minor behind. Fine. |
| `SQLAlchemy` | 2.0.48 | 2.0.52 | 4 patches behind. Fine. |
| `httpx` | 0.28.1 | 0.28.1 | Current. |
| `h11` | 0.16.0 | 0.16.0 | Current (0.16.0 is the CVE-2025-43859 fix release). |
| `certifi` | 2026.2.25 | 2026.7.22 | 5 months of CA-bundle drift. No advisory, but refresh it. |

---

## 4. Prioritized remediation table

`Risk` = breaking-change risk. **None** = same major, inside existing range. **Minor** = same major, several versions of drift. **MAJOR** = crosses a major boundary.

### P0 — do first (runtime-exposed, and cheap)

| # | Package | Current | Target | Severity | Direct/Trans | Dev/Runtime | Risk | Test after |
|---|---|---|---|---|---|---|---|---|
| 1 | `react-router-dom` (+ `react-router`) | 7.13.1 | **7.18.2** | **HIGH** (12 adv, incl. CVSS 8.1) | Direct (`react-router` trans, exact-pinned by parent) | **RUNTIME — shipped** | **None** (`^7.13.1` covers it) | Full nav: `/` → login → `pages/dashboard.jsx`; `npm test` — `App.test.jsx`, `login.test.jsx`, `register.test.jsx` |
| 2 | `pyasn1` | 0.6.2 | **0.6.4** | **HIGH ×4** (all 7.5 DoS) | Transitive (`python-jose`, `google-auth`) | RUNTIME | **None** (patch) | `pytest tests/test_auth.py tests/test_security.py`; issue + verify a JWT round-trip |
| 3 | `urllib3` | 2.6.3 | **2.7.0** | **HIGH ×2** (7.5) | Transitive (`requests`) | RUNTIME | **None→Minor** | `pytest tests/test_execute.py tests/test_validate_key.py`; live Gemini call (`google-genai` → `requests`) |
| 4 | `httplib2` | 0.31.2 | **0.32.0** *(or delete via H-4)* | **HIGH** (7.5) | Transitive (`google-api-python-client`) | RUNTIME | **None** | Prefer removing `google-generativeai` — then re-run the full `pytest` suite |
| 5 | `cryptography` | 46.0.5 | **46.0.7** | Moderate + Low *(partial)* | Transitive (`google-auth`) | RUNTIME | **None** (patch) | Gemini auth path: `pytest tests/test_execute.py` |
| 6 | `idna` | 3.11 | **3.15+** (latest 3.19) | Moderate | Transitive (`email-validator`, `httpx`) | RUNTIME | **None** | Registration with unicode/IDN email domains: `pytest tests/test_auth.py` |

### P1 — schedule (dev-only, or needs a coordinated bump)

| # | Package | Current | Target | Severity | Direct/Trans | Dev/Runtime | Risk | Test after |
|---|---|---|---|---|---|---|---|---|
| 7 | `vitest` | 4.0.18 | **4.1.11** | **CRITICAL** (9.8) | Direct | **DEV-ONLY** (UI server not used) | **None** (`^4.0.18` covers it) | `npm test` — all 19 test files must pass |
| 8 | `vite` | 7.3.1 | **7.3.6** | HIGH | Direct | **DEV-ONLY** | **None** (`^7.3.1` covers it) | `npm run dev`, `npm run build`, `npm run preview` |
| 9 | `eslint` + `@eslint/js` | 9.39.3 | **9.39.5** | HIGH (via `js-yaml`, `brace-expansion`, `flatted`) | Direct | **DEV-ONLY** | **None** (`^9.39.1` covers it) | `npm run lint` — flat config in `eslint.config.js` must still resolve |
| 10 | `@vitejs/plugin-react` | 5.1.4 | **5.2.0** | Low (via `@babel/core`) | Direct | **DEV-ONLY** | **None** | `npm run build`; React Fast Refresh in `npm run dev` |
| 11 | `jsdom` transitive `undici` | 7.22.0 | **≥7.29.0** | HIGH ×5 + 9 mod + 2 low | Transitive (`jsdom`) | **DEV-ONLY** | **None** (`^7.21.0` covers it) | `npm test` — jsdom environment must still boot |
| 12 | **`starlette` + `fastapi` together** | 0.52.1 / 0.135.1 | **1.6.0 / 0.141.1** | **HIGH ×2** + 2 mod + 1 low | Transitive (pinned) + Direct | RUNTIME | ⚠️ **MAJOR** (starlette 0→1) | Full `pytest` suite (11 modules); CORS preflight from `localhost:5173` and the Vercel origin; every route in `app/api/`. **Bump both together — never starlette alone.** |
| 13 | `requests` | 2.32.5 | **2.33.0+** | Moderate | Transitive | RUNTIME | **None→Minor** | `pytest tests/test_execute.py` |
| 14 | `pytest` | 9.0.2 | **9.0.3** | Moderate | Direct | **DEV-ONLY** | **None** (patch) | Full `pytest` suite |
| 15 | `Pygments` | 2.19.2 | **2.20.0** | Low | Transitive (`pytest`) | **DEV-ONLY** | **None** | Full `pytest` suite |
| 16 | `click` | 8.3.1 | **8.3.3** | unrated (local/high-priv) | Transitive (`uvicorn`) | runtime tooling | **None** | `uvicorn app.main:app --reload --port 8000` starts |
| 17 | `esbuild`/`postcss`/`nanoid`/`picomatch` | — | carried by `vite` 7.3.6 | High/Low | Transitive | **DEV-ONLY** | **None** | Covered by #8 |
| 18 | `ecdsa` | 0.19.1 | **0.19.2** *(partial — CVE-2024-23342 stays open)* | **HIGH, unfixable** | Transitive (`python-jose`) | RUNTIME | **None** | `pytest tests/test_auth.py`. ⚠️ **No fix exists for Minerva.** Not reachable — app is HS256-only. |

### P2 — hygiene / strategic (no advisory driving them)

| # | Change | Rationale | Risk | Test after |
|---|---|---|---|---|
| 19 | **Remove `passlib==1.7.4`** | Unused, abandoned since 2020, **and empirically broken with the pinned `bcrypt==5.0.0`** (H-1) | **None** — nothing imports it | `pytest tests/test_security.py tests/test_auth.py` |
| 20 | **Remove `google-generativeai` + `google-ai-generativelanguage` + `google-api-python-client`** | Deprecated legacy Gemini SDK, unused; removal deletes the `httplib2` HIGH (B-6) and 5 other packages | **None→Minor** — confirm nothing imports `google.generativeai` (verified: nothing does) | `pytest tests/test_execute.py`; live Gemini call |
| 21 | **Remove `requests`** from `requirements.txt` as a top-level pin | Not imported; let `google-api-core` resolve it | **None** | Full `pytest` |
| 22 | **Split `requirements.txt` into direct-only + a real lockfile** | The current file is a `pip freeze` dump; pinned transitives block security upgrades (§3.1) | Minor — must re-resolve | Full `pytest` + `uvicorn` boot |
| 23 | **Create a `backend/.venv`** | Deps currently live in system Python 3.13 alongside jupyter/streamlit/flask | **None** | Full `pytest` in the fresh venv |
| 24 | **Migrate `python-jose` → `PyJWT`** | Drops `ecdsa` (unfixable HIGH), `rsa`, `pyasn1` (4 HIGHs). App is HS256-only, so this is a small diff | **Minor** — `jwt.encode/decode` signatures differ; `JWTError` → `PyJWTError` | `pytest tests/test_auth.py tests/test_security.py`; verify existing tokens still validate |
| 25 | `certifi` 2026.2.25 → 2026.7.22 | 5 months of CA-bundle drift | **None** | Any outbound HTTPS call |
| 26 | Reconcile `grpcio` 1.78.0 / `grpcio-status` 1.71.2 skew | These ship in lockstep; 7 minors apart is a resolution artifact | Minor | Full `pytest` |
| 27 | Provider SDK majors: `openai` 2.26.0→3.3.1, `anthropic` 0.84.0→1.0.0, `google-genai` 1.66.0→2.19.0 | No advisories — but three simultaneous majors on the core feature path | ⚠️ **MAJOR ×3** | `app/providers/*.py` all three; `pytest tests/test_execute.py tests/test_validate_key.py`; live call per provider |
| 28 | Frontend `react`/`react-dom` 19.2.4 → 19.2.8 | 4 patches behind, no advisory | **None** | `npm test`, `npm run build` |
| 29 | Frontend majors: `eslint` 10, `jsdom` 29, `@testing-library/jest-dom` 7, `vite` 8, `globals` 17, `eslint-plugin-react-refresh` 0.5 | **Not required for any advisory** — see §2.5 Group B | ⚠️ **MAJOR** | Defer; take individually with full `npm test` + `npm run lint` |

---

## 5. Dependency hygiene

### H-1 · 🔴 `passlib==1.7.4` is pinned, unused, abandoned, and **provably broken** with the pinned `bcrypt==5.0.0`

`grep -rn "passlib" backend --include="*.py"` → **no matches.** Nothing in `app/` or `tests/` imports it. `app/utils/security.py` uses raw bcrypt:

```python
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
```

I confirmed the known passlib/bcrypt incompatibility **empirically** in the installed environment (read-only, no mutation):

```
(trapped) error reading bcrypt version
Traceback (most recent call last):
  File ".../site-packages/passlib/handlers/bcrypt.py", line 620, in _load_backend_mixin
    version = _bcrypt.__about__.__version__
              ^^^^^^^^^^^^^^^^^
AttributeError: module 'bcrypt' has no attribute '__about__'
bcrypt version: 5.0.0
has __about__: False
PASSLIB FAILED: ValueError password cannot be longer than 72 bytes, truncate manually if necessary
```

`passlib.context.CryptContext(schemes=["bcrypt"]).hash(...)` **raises**. passlib 1.7.4 (2020) reads `bcrypt.__about__.__version__`, removed in bcrypt 4.1+; against bcrypt 5.0.0 it degrades further into a hard `ValueError`.

**Impact today: none** — the app bypasses passlib entirely. **Impact tomorrow: a landmine.** Any developer who reaches for the standard FastAPI-tutorial `CryptContext` pattern will hit a runtime auth failure that looks like a code bug. **Remove `passlib` from `requirements.txt`.**

*(Secondary note, unrelated to passlib: `bcrypt.hashpw` silently ignores input beyond 72 bytes. `app/utils/security.py` does not length-check `password`, so passwords longer than 72 bytes are truncated. Flagged for awareness — not a dependency issue.)*

### H-2 · 🟡 `requirements.txt` is a `pip freeze` dump — pinned transitives block security upgrades

Detailed in §3.1. 64 entries, all `==`, strict-alphabetical with `pip freeze` casing, and ~51 of the 64 are transitive. **The concrete harm:** `starlette==0.52.1` (5 advisories, 2 HIGH) will not move when you bump `fastapi`, because the pin wins. Same for `urllib3`, `pyasn1`, `idna`, `cryptography`, `httplib2` — every one of the runtime HIGHs in §3.4 is a **pinned transitive**. Fixing them requires editing lines that look like they belong to nobody.

**Recommend:** a hand-written direct-only manifest (~14 packages) plus a generated lockfile (`pip-compile`, `uv pip compile`, or `pip freeze > requirements.lock`).

### H-3 · 🟡 No lockfile and no hash pinning (Python)

No `poetry.lock`, `Pipfile.lock`, `uv.lock`, `pyproject.toml`, or `requirements.lock` anywhere in the repo. No `--hash=` entries and no `--require-hashes`. Exact `==` pins give version reproducibility but **not artifact integrity** — a compromised or re-uploaded PyPI artifact at the same version would install silently.

### H-4 · 🟡 Two Gemini SDKs pinned; the app uses only one

`requirements.txt` pins **both**:
- `google-genai==1.66.0` — the current SDK, **and the one actually used**: `app/providers/gemini_provider.py:7` and `app/services/llm_service.py:16` both do `from google import genai`.
- `google-generativeai==0.8.6` — Google's **deprecated legacy SDK**. `grep -rn "google.generativeai"` → **no matches.** Never imported.

`google-generativeai` drags in **`google-ai-generativelanguage==0.6.15`** (hard-pinned by its metadata), **`google-api-python-client`**, **`google-auth-httplib2`**, **`httplib2`**, **`uritemplate`**, and **`pyparsing`**.

**This unused package is the sole reason `httplib2` (B-6, HIGH, CVE-2026-59939) is in the tree at all.** Removing it deletes a HIGH advisory and 6 packages of attack surface for zero functional cost.

### H-5 · 🟡 `requests==2.32.5` pinned top-level but never imported

`grep -rn "import requests"` → **no matches.** It arrives via `google-api-core` and `google-genai`. Pinning it top-level makes it look like a chosen dependency and means its Moderate advisory (B-7) needs a manual bump.

### H-6 · 🟢 No dependency is imported but missing from a manifest — **both ecosystems clean**

**Backend:** every third-party module imported across `app/` and `tests/` — `fastapi`, `sqlalchemy`, `pydantic`, `jose`, `bcrypt`, `dotenv`, `openai`, `anthropic`, `google.genai`, `pytest` — has a matching pin. No missing declarations.

**Frontend:** every non-relative specifier in `src/` — `react`, `react-dom/client`, `react-router-dom`, `@testing-library/react`, `@testing-library/jest-dom` (in `src/test/setup.js`), `vitest` — is declared in `package.json`. No phantom imports.

**`python-multipart` note:** not in `requirements.txt` and **not needed** — `grep -rn "UploadFile\|Form(\|multipart"` returns **NONE FOUND**. The app is JSON-only. FastAPI only requires it under the `[standard]` extra or when form/file params exist. **Correctly absent — not a finding.** (Worth remembering if a file-upload endpoint is ever added: it would need to be added explicitly, and it would also make starlette CVE-2026-54283 live.)

### H-7 · 🟢 Declared-but-unused (both ecosystems)

**Frontend — `@types/react` (19.2.14) and `@types/react-dom` (19.2.3):** there is **no TypeScript in this project** — no `tsconfig.json`, and `find src -name "*.ts" -o -name "*.tsx"` returns nothing. Every file is `.js`/`.jsx`. These are inert leftovers from the Vite React scaffold. Harmless (they only feed editor IntelliSense) but they are two dev dependencies with no build role. Low priority.

**Backend — `pytest-asyncio==1.3.0`:** pinned, but there is no `asyncio_mode` setting anywhere (no `pytest.ini`, `pyproject.toml`, `setup.cfg`, or `tox.ini` in the repo) and no `@pytest.mark.asyncio` in the 11 test modules. Likely unused. Verify before removing.

### H-8 · 🟢 Lockfile duplicates (frontend) — minor, all benign

`package-lock.json` is `lockfileVersion: 3` with **299 `node_modules` entries**. Five packages resolve to more than one version:

| Package | Versions |
|---|---|
| `ansi-styles` | 4.3.0, 5.2.0 |
| `dom-accessibility-api` | 0.5.16, 0.6.3 |
| `eslint-visitor-keys` | 3.4.3, 4.2.1 |
| `globals` | 14.0.0, 16.5.0 |
| `lru-cache` | 5.1.1, 11.2.6 |

**None is a vulnerable package**, and none is a version *conflict* — they are normal peer-range splits between the ESLint and Vitest/Testing-Library subtrees (e.g. `@eslint/eslintrc` needs `globals@^14`, the root config needs `globals@^16`). No action needed. **Note there are no duplicate entries for any of the 13 vulnerable packages**, which is why every one of them can be fixed by a single lockfile bump.

### H-9 · 🟡 No virtualenv for the backend

`backend/.gitignore` contains only `*.db`. There is no `.venv`, `venv`, or `env` directory, and `README.md:130` instructs a bare `pip install -r requirements.txt`. Confirmed: PromptBox's 64 packages are installed into the **system-wide Python 3.13.7** alongside 129 unrelated packages (`jupyterlab`, `streamlit`, `Flask`, `pandas`, `scikit-image`, …). Consequences: dependency resolution for PromptBox can be silently altered by unrelated installs; `pip list` cannot tell you what this project actually needs; and any future `pip install -U` for PromptBox risks breaking the user's Jupyter/Streamlit setup.

### H-10 · 🟢 Positive findings worth recording

- **JWT decode pins the algorithm.** `app/dependencies/auth.py:19` uses `algorithms=["HS256"]` explicitly — this closes the algorithm-confusion class of JWT attack (the class behind python-jose's historical CVE-2024-33663) and is why the `ecdsa` Minerva CVE is unreachable.
- **All 64 backend pins match what is installed** — zero drift between `requirements.txt` and reality.
- **The frontend ships only 3 runtime dependencies** (`prod: 8` total resolved), so the blast radius of the 12 dev-only advisories is genuinely confined to developer machines and CI.
- **`h11` is at 0.16.0**, the release that fixed the request-smuggling CVE-2025-43859 — correctly current.
- **No advisory in either ecosystem requires a forced/`--force` npm fix.**

---

## Appendix A — `npm audit` (human-readable, verbatim tail)

```
13 vulnerabilities (2 low, 10 high, 1 critical)

To address all issues, run:
  npm audit fix
```

## Appendix B — commands run (all read-only; nothing was mutated)

```
npm audit                      # frontend/
npm audit --json               # frontend/
npm outdated                   # frontend/
npm ls <pkg> --all             # frontend/, for each of the 13 vulnerable packages
pip-audit --help               # -> command not found (NOT installed, per constraint)
safety --version               # -> command not found (NOT installed, per constraint)
python3 -m pip list --format=json
POST https://api.osv.dev/v1/querybatch      # 64 PyPI packages, by exact pinned version
GET  https://api.osv.dev/v1/vulns/{id}      # full record for each of the 25 advisories
GET  https://pypi.org/pypi/{pkg}/json       # latest version + release dates
grep / find / cat              # source and manifest inspection
```

**No `npm audit fix`, `npm update`, `npm install`, `pip install`, or `pip install -U` was run. `package.json`, `package-lock.json`, and `requirements.txt` are unmodified. The only file written by this audit is this report.**
