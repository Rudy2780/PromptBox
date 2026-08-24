# PromptBox — Audit Summary & Prioritized Backlog

**Date:** 2026-08-24
**Scope:** full repo at `main` (`2dc37bb`), plus the unmerged `origin/cleanup/codebase` branch (`f26fa18`)
**Source reports:** [AUDIT_FEATURES.md](AUDIT_FEATURES.md) · [AUDIT_SECURITY.md](AUDIT_SECURITY.md) · [AUDIT_QUALITY.md](AUDIT_QUALITY.md) · [AUDIT_DEPENDENCIES.md](AUDIT_DEPENDENCIES.md)

---

## Read this first: three corrections to the project's stated premise

All four audits independently converged on the same conclusion, so it is stated once here rather than repeated per section.

### 1. The stack description is wrong in ways that block the roadmap

| Claimed | Actual |
|---|---|
| PostgreSQL | **SQLite** (`backend/app/config.py:7`) — and **no Postgres driver exists in `requirements.txt`** (no `psycopg2`, no `asyncpg`). Pointing `DATABASE_URL` at Postgres today crashes `create_engine` at import. |
| GitHub + Google OAuth | **None.** Email+password → bcrypt → JWT HS256/24h. Zero repo-wide hits for `oauth`, `authlib`, `client_secret`, `redirect_uri`. No OAuth library in requirements. |
| Deployed on Vercel + Render | **True at runtime, but nothing is versioned.** No `vercel.json`, `render.yaml`, `Procfile`, `Dockerfile`, or CI anywhere in the repo. Deploy config — *including whether `JWT_SECRET` is set* — exists only in dashboards. This is why P0-1 below is critical rather than theoretical. |
| React + Vite, FastAPI | Accurate. |

### 2. The pivot has not started in code

Zero repo-wide hits for `codegen`, `evaluat*`, `rubric`, `judge`, `benchmark`, `pass@`, `ollama`, or any sandbox primitive. Of the eight roadmap items, **seven are NOT STARTED**; the eighth (code diffing) diffs the wrong thing.

The practical consequence is good news: **the dead code in this repo is not pivot residue.** It traces to three ordinary incidents — an `API_BASE` find-and-replace that missed four files, a single→multi-model refactor that left both branches alive, and a template-category rename applied inconsistently. There is no half-built evaluation platform to demolish or work around. **Phase 2 is greenfield on a working foundation, not a rescue.**

### 3. Parts of the roadmap are already built

**Side-by-side multi-model comparison is fully wired** — `POST /api/prompt` executes a prompt across a mixed list of providers in one request and renders a response-card grid. It was listed as planned. Also already shipped and unmentioned: full prompt version CRUD with debounced search, export to txt/md/json, and parallel per-provider key validation gating the Execute button.

**Test coverage is the strongest part of the repo:** 10 backend pytest files (59 passing) and 17 frontend vitest files (52 passing, 4 failing — all four from one root cause, P1-7).

---

## Priority model

| | Meaning |
|---|---|
| **P0** | Fix before resuming feature development. Live security exposure or a latent data-destroying defect. |
| **P1** | Fix during the next work cycle. Real user-facing bugs, reachable vulnerabilities, and blockers that Phase 2 will hit. |
| **P2** | Cleanup, hardening, and hygiene. Safe to batch. |

Severity is reachability-adjusted throughout: a CVSS 9.8 whose precondition does not exist in this codebase is ranked below a CVSS 7.5 that sits directly on the auth path. Where a rating was lowered, the reason is stated.

---

# P0 — Before resuming development

### P0-1 · Forgeable JWTs: signing secret falls back to a value the README publishes
`backend/app/config.py:8` · `README.md:100` · *(Security C1)*

`JWT_SECRET = os.getenv("JWT_SECRET") or "dev-secret-change-me"`, and the README documents that exact string in a defaults table. HS256 is symmetric (`auth_service.py:25`, `dependencies/auth.py:19`), so if the Render env var is unset — **nothing in the repo sets, enforces, or version-controls it** — anyone can sign `{"sub":"1","exp":...}` and become any user. User IDs are sequential integers (`models/user.py:9`), so enumerating every account is a loop. Grants read/rename/delete on any user's saved prompts and export of any user's prompt text. The repo is public on GitHub; treat the fallback as known to attackers.

Note the `or` also means an env var set to an **empty string** silently falls back to the same default.

**Do:** replace with `os.environ["JWT_SECRET"]` plus a startup length assertion that fails fast; generate a fresh secret; **rotate — assume outstanding tokens may be forged**; delete the value from `README.md:100`. Set the same var in Render before deploying the change.

### P0-2 · The test suite mass-deletes users and prompts from the configured database
`backend/tests/conftest.py:8-21` · *(Security H2 + Quality, independently found)*

An `autouse=True` fixture calls `db.query(PromptVersion).delete()` and `db.query(UserInfo).delete()` against `SessionLocal` from `app.database` — **the real configured engine**. No test-DB override, no `dependency_overrides`. It runs before *and* after every test. Importing `app.main` additionally fires `create_all` and a live `ALTER TABLE` at module scope (`main.py:9,16,18`).

`README.md:93` instructs developers to put `DATABASE_URL` in `backend/.env`; `README.md:166` instructs them to run `pytest tests`. Following both against a shared or production database silently destroys all data. **This is currently survivable only because the DB is local SQLite — it becomes production-destroying the moment P1-1 lands.** Fix it before the Postgres migration, not after.

**Do:** dedicated test engine + `app.dependency_overrides[get_db]`; add a hard `assert "test" in str(engine.url)` guard; move `create_all`/`ALTER TABLE` out of module scope into an explicit migration (Alembic).

### P0-3 · The three LLM endpoints have no authentication and no rate limiting
`routes_execute.py:46,71` · `routes_validate_key.py:28` · *(Security H1)*

None of `/api/execute`, `/api/prompt`, `/api/validate-key` declares `Depends(get_current_user)` — unlike `routes_versions.py:17` and `routes_export.py:38`, which correctly do. The backend URL is a public constant in the shipped bundle. No rate-limiting dependency exists in `requirements.txt`. CORS does not mitigate any of this; `curl` ignores it.

Three distinct abuses:
1. **`/api/validate-key` is a stolen-key validation oracle** — submit candidate keys, get 200/401 against OpenAI, Anthropic, and Gemini, anonymously, unthrottled, from your IP. This is the sharpest of the three.
2. **`/api/execute` is an open LLM relay**, laundering third-party traffic through your Render instance.
3. **`/api/prompt` loops `request.models` with no length cap** and no `max_length` on `prompt` (`execute_schema.py:6,18-19`), each iteration a blocking network call — one request can hold a worker for minutes.

**Do:** add `get_current_user` to all three (the frontend already holds `user.token`); rate-limit per user and per IP; bound `prompt` (~32k) and `models` (~4, de-duplicated).

**Sequencing note:** P0-1 and P0-3 must be fixed *before* the sandboxed-execution feature ships, or an auto-execution endpoint inherits a forgeable token and an established no-auth pattern.

---

# P1 — Next work cycle

### P1-1 · SQLite on Render's ephemeral disk — silent total data loss on every redeploy
`backend/app/config.py:7` · *(Security M4)*

Unless a persistent disk is attached, every deploy wipes all users and saved prompts. Also single-writer, so it will lock-contend under any concurrency.

> **Promote to P0 if the deployed instance has real users.** Verify current Render disk configuration before deciding.

Blocked by the missing driver (see premise correction #1) and gated by P0-2. Sequence: fix P0-2 → add `psycopg2-binary` → introduce Alembic → migrate → then attach or drop the SQLite path.

### P1-2 · Anthropic failures are reported to users as "invalid API key"
`backend/app/providers/anthropic_provider.py:42` · *(Features + Quality)*

The generic fallthrough raises `ProviderAuthError` (→401) where OpenAI (`:54`) and Gemini (`:47`) correctly raise `ProviderError` (→502). Every rate limit, timeout, network blip, or bad model ID on a Claude call surfaces as **401 "invalid API key."** Users will rotate keys that were never broken. One-word fix. No Anthropic provider test exists to catch it.

### P1-3 · A failed key validation bricks the UI until reload
`frontend/src/components/ModelSelector.jsx:56-76` · *(Quality)*

The only async handler in the codebase with no `try/catch`. A rejected fetch skips `setLoading(false)`, pinning the button at "Validating…" forever — and since it gates Execute, the app is unusable. **Highly likely on Render free-tier cold starts**, which is exactly when a new user first touches the app.

### P1-4 · `react-router-dom` 7.13.1 — the only vulnerable package that ships to users
12 advisories. Fix is **7.18.2, inside the existing `^7.13.1` range — no major bump.**

Reachability-adjusted: the headline advisories (turbo-stream deserialization RCE, CVSS 8.1; RSC XSS, 8.0; RSC CSRF bypass) are **SSR/RSC-specific and not reachable** — this is a client-side SPA with no SSR or prerender. What *is* live: two open-redirects (backslash in `<Link>`, protocol-relative `//`) and route-matching DoS. Patch-level, free.

### P1-5 · Backend security patches on the auth and credential paths
All patch-level, no major bumps, no breaking risk:

- **`pyasn1` 0.6.2 → 0.6.4** — 4 × HIGH (CVSS 7.5) unauthenticated DoS, sitting on the JWT auth path via `python-jose`. **Best value-to-risk ratio in the entire audit.**
- **`urllib3` 2.6.3 → 2.7.0** — CVE-2026-44431 forwards sensitive headers cross-origin on proxied redirects. Elevated here specifically because **this app forwards user-supplied provider API keys**.
- **`cryptography` 46.0.5 → 46.0.7** — clears 2 of 6 advisories for free. (Full clearance needs ≥48.0.1, a 4-major jump — deferred to P2-14.)

### P1-6 · Delete two dependencies that are pinned, unused, and actively harmful
- **`google-generativeai==0.8.6`** — the deprecated legacy Gemini SDK, **never imported** (code uses `from google import genai`). It is the *sole* reason `httplib2` and its HIGH decompression-bomb CVE are in the tree. Removing it deletes 6 packages and one HIGH **at zero cost**.
- **`passlib==1.7.4`** — unused, abandoned since 2020, and **verified already broken** against the pinned `bcrypt==5.0.0` (reproduces `AttributeError: module 'bcrypt' has no attribute '__about__'`, then a hard `ValueError` on `.hash()`). Inert today because `utils/security.py` calls raw bcrypt — a landmine for anyone reaching for the standard FastAPI `CryptContext` pattern.

Related, same area: **`google-generativeai`'s transport passes the API key as a `?key=` query param.** Combined with P1-9's error-text leakage, one client swap would turn those lines into direct key disclosure. Removing the package removes that future footgun.

### P1-7 · Four failing frontend tests, stale generated docs, and a false README claim — one root cause
`API_BASE` is hardcoded in **6 files** (5 under `src/api/`, plus `Login.jsx:8`). Someone changed it from `localhost:8000` to the Render URL and missed the 4 test files and the JSDoc output. That single miss causes **all 4 test failures**, **all** the staleness in `frontend/docs/`, and the false claim at `README.md:155`.

A second, security-relevant consequence *(Security M5)*: a developer running `npm run dev` locally and pasting a **real provider key** sends it to the **production** Render host — where P1-9's `print()` statements may write the resulting error into shared logs.

One `import.meta.env` config fixes all of it. **The `cleanup/codebase` branch already implements this** (adds `src/api/config.js`) — see P2-1.

### P1-8 · Passwords of 73–128 characters cause HTTP 500 on both register and login
`schemas/auth.py:5` allows `max_length=128`; `bcrypt==5.0.0` raises `ValueError` above 72 **bytes** (verified against the installed library). Long passphrases and multi-byte (emoji/CJK) passwords fail at `/auth/register`; any such account that existed would be **permanently locked out** at `/auth/login`. Cap at 72 bytes with a clear validation error, or pre-hash.

### P1-9 · Raw provider exception text reaches unauthenticated callers and production logs
`llm_service.py:70,73` `print()`s exception bodies into Render logs; `openai_provider.py:54`, `gemini_provider.py:47`, `anthropic_provider.py:42` interpolate `{exc}` into messages returned as HTTP `detail` (`routes_execute.py:63,66,96,98`) and displayed in the browser. All three SDKs pass keys in headers, so key disclosure is unlikely *today* — but see the `google-generativeai` note in P1-6.

Related: **`test_anthropic_key` is defined twice** in `llm_service.py` (`:40` and `:60`); the second silently wins, uses a different model, and is the one carrying the `print()`s. **Fixed on the `cleanup/codebase` branch.**

### P1-10 · A fresh deploy has no `templates` table
`main.py:9`'s `create_all` omits the `Template` model, so the table exists only where the manual seed script happened to run. Any clean environment — including a fresh Render instance — serves a broken template library.

### P1-11 · Planning constraint: `requirements.txt` is a `pip freeze` dump, not a manifest
64 entries, all `==`, ~51 of them transitive. **Every runtime HIGH in this audit is a pinned transitive**, which means bumping `fastapi` will *not* move `starlette`. This file must be regenerated wholesale from a real top-level manifest rather than patched line by line. Also: no virtualenv (deps sit in system Python 3.13.7 beside ~129 unrelated packages), no lockfile, no hash pinning.

### P1-12 · Planning constraint: `starlette` and `fastapi` must move together
`starlette` 0.52.1 → 1.x is a 0.x→1.x major. `fastapi==0.135.1` declares `starlette>=0.46.0` with **no upper cap**, so pip will happily accept it — but FastAPI 0.135.1 predates Starlette 1.0 and was never tested against it. **Bump `fastapi`→0.141.1 and `starlette`→1.6.0 as one change; never starlette alone.**

Mitigating context: of starlette's 5 advisories, source grep confirms **no `StaticFiles`, no `HTTPEndpoint`, no `request.form()`** — so most are not currently reachable. This is a scheduled upgrade, not an emergency.

---

# P2 — Cleanup and hardening

### P2-1 · Land `origin/cleanup/codebase` (highest leverage item in P2)
Refactor-only, no features, and it already resolves: **P1-7** (adds `src/api/config.js`, centralizing `API_BASE`), **P1-9's duplicate function** (removes the shadowed `test_anthropic_key` and its `print()`s), the misspelled filenames (`DiffVerisonPicker`→`DiffVersionPicker`, `vesrionsApi`→`versionsApi`, `dashboard`→`Dashboard`), the triplicated model allowlist (extracts `backend/app/supported_models.py`), and the empty `Navbar.jsx` and unused `react.svg`.

**Review two things before merging:** it deletes `Login.test.jsx` (48 lines of coverage), and it does **not** touch `config.py` or route auth — **it clears none of P0**. Landing it is not a substitute for the P0 work.

### P2-2 · ESLint reports 118 problems — 107 are a single config bug
`eslint.config.js:18` never declares vitest globals. Only **5 of 118 problems are in non-test source**. A 4-line config block makes `--max-warnings=0` a realistic CI gate. *(Note: `--reporter=basic` does not exist in Vitest 4; use `dot`.)*

### P2-3 · Dead and unreachable code
- `Navbar.jsx` — **0-byte file**, imported nowhere *(fixed on cleanup branch)*
- `ErrorMessage.jsx` — orphaned; `dashboard.jsx:125` inlines its own red `<p>` instead
- Unused assets: `email.png`, `password.png`, `person.png`, `react.svg`
- **`POST /api/execute` is unreachable in the running app** — `dashboard.jsx:79-87` always passes `models`, so `PromptEditor.jsx:29`'s single-model branch is dead outside tests. Decide: delete the endpoint, or route single-model through it.
- Backend-only, no UI: `GET /api/versions/{id}`, `GET /api/templates/{id}`, `getHealth`
- Byte-identical duplicated chevron CSS: `App.css:216-229` ≡ `ExportDropdown.css:18-31`
- `@types/react` / `@types/react-dom` declared with **no TypeScript in the project**

### P2-4 · Auth UX defects
- **Login "Name" field is collected but never sent** and has no DB column (`Login.jsx:92-97` vs `:51`)
- **"Continue as Guest" produces a broken dashboard** — passes `null`, clearing App's `undefined` gate, so the page renders but every `{user && ...}` panel silently vanishes
- **No `localStorage` anywhere → refresh logs the user out.** (Upside: this is also why there is no XSS-readable token store — see Clean Bill below. Preserve that property when fixing; prefer an httpOnly cookie or in-memory + refresh flow over `localStorage`.)

### P2-5 · Token lifecycle
24-hour JWTs with no `jti`/`iat`/`aud`/`iss` (`auth_service.py:20-25`), so a denylist is impossible and **logout is `setUser(undefined)` in React only** (`App.jsx:19`). `README.md:183`'s "short-lived" claim is inaccurate.

### P2-6 · No login throttling; `/auth/register` returns 409 → account enumeration
Login itself is correctly constant-response. Registration leaks which emails exist, and bcrypt cost-12 per guess makes it a cheap CPU-exhaustion vector.

### P2-7 · `/docs`, `/redoc`, `/openapi.json` public in production
`main.py:20` — with a Try-It-Out button pointed at the unauthenticated endpoints from P0-3. Disable in prod or gate behind auth. *(Drops to cosmetic once P0-3 lands.)*

### P2-8 · Assorted backend hardening
- `int(user_id)` outside the `try` → 500 instead of 401 (`dependencies/auth.py:32`)
- `LIKE` wildcards unescaped in search (`routes_versions.py:44`) — **not injection**, parameters are bound; a user searching `%` matches everything
- `allow_credentials=True` unnecessary for a Bearer-only app (`main.py`)
- `model_config` declared outside the class (`routes_templates.py:18`)
- `/api/templates/*` unauthenticated — low impact, static seeded content

### P2-9 · Two client-construction layers per provider
`llm_service.py` **bypasses** `app/providers/*` and builds its own clients. (The providers are *not* orphaned — they are correctly wired at `routes_execute.py:12,31-32`.) Two paths to maintain, and it is why the P1-2 bug could exist in one and not the other. Collapse onto the provider layer.

### P2-10 · README corrections
Lines 100 (JWT default — **P0-1**), 50/93/180 (PostgreSQL vs SQLite), 155 (`API_BASE`), 183 ("short-lived" tokens), and **109-110, which publish demo credentials `demo@example.com` / `password123`** — confirm that account does not exist on the deployed instance.

### P2-11 · `vitest` 4.0.18 — CVSS 9.8, effectively unexposed
GHSA-5xrq-8626-4rwp (arbitrary file read+execute) **requires the Vitest UI server to be listening**. Scripts are `vitest run` / `vitest`, neither enables UI, and `@vitest/ui` is not installed. Real exposure ≈ zero. Fix to 4.1.11 (inside `^4.0.18`) because it is free, not because it is urgent — **this is why it is P2 and not P0 despite the 9.8**.

### P2-12 · Dev-only frontend advisories
`vite` 7.3.1 (5 advisories, dev-server file read + two `server.fs.deny` bypasses, two Windows-only; fix 7.3.6 in-range), `undici` 7.22.0 via `jsdom` (16 advisories, confined to the test runner), plus in-range transitives `postcss`, `js-yaml`, `brace-expansion`, `flatted`, `nanoid`, `picomatch`. **12 of 13 frontend findings never reach a user.** All fixable by lockfile bump alone — `npm audit` reports `fixAvailable: true` for all 13 with **no `--force` and no major bump required**.

### P2-13 · `ecdsa` 0.19.1 / CVE-2024-23342 (Minerva) — no fix exists, not reachable
The only advisory in either ecosystem with **no fixed version** (0.19.2 does not fix it). Not exploitable here: the app is HMAC-only (`algorithm="HS256"`, and decode correctly pins `algorithms=["HS256"]`), so no ECDSA operation ever runs. Dead weight from `python-jose`. Track only — or drop `python-jose` for `pyjwt`, which would also remove `pyasn1` and `rsa` from the tree.

### P2-14 · Deferred major bumps — do not bundle with security work
- **`cryptography` 46 → 50** (4 majors) to fully clear the bundled-OpenSSL HIGH. Mitigated by P1-5's free 46.0.7 patch. The app never imports it directly (arrives via `google-auth`).
- **Provider SDKs, each one full major behind:** `openai` 2.26→3.3.1, `anthropic` 0.84→**1.0.0**, `google-genai` 1.66→2.19. **No advisories on any of them** — this is pure churn risk on the core feature path (`app/providers/*.py`). Schedule separately, with the provider tests green first.

---

# Clean bill of health — verified, not assumed

Worth recording so nobody re-audits these, and so the good properties are **preserved rather than accidentally regressed** during Phase 2:

- **No secrets ever committed.** Full `--all` history scan: no `.env` or `.db` tracked in any ref. `backend/promptbox.db` is correctly ignored (`backend/.gitignore:1`), both `.gitignore` files date from the initial commit (no ignored-after-the-fact gap), and the file on disk is empty — 0 users, 0 versions, no key-shaped strings.
- **Provider keys are never persisted and never leak to the bundle.** Browser state → `type="password"` inputs → JSON request **body** (not URL, so out of access logs and `Referer` headers) → provider constructor. No DB column, no `open()`/`write()` in the backend, never echoed in success responses. **No `import.meta.env` or `VITE_` reference exists anywhere in the frontend**, and there is no `frontend/.env`. Only residual exposure is P1-9.
- **Object ownership is textbook-correct — no IDOR.** Every version and export handler filters `user_id` and `id` in the same query; `user_id` on create comes from the authenticated principal, not the request body; missing rows 404 rather than 403.
- **No SQL injection.** All ORM; the only raw SQL is a static DDL literal (`main.py:16`).
- **No XSS surface.** Zero hits for `dangerouslySetInnerHTML` / `innerHTML` / `document.write` / `new Function` / `eval(` across `frontend/src`. Model output renders as an escaped JSX text child in `<pre>`.
- **Token storage is better than typical.** No `localStorage` / `sessionStorage` / `document.cookie` anywhere, so XSS cannot exfiltrate a token from storage. (This is the flip side of P2-4's refresh-logout bug — **fix that without introducing `localStorage`.**)
- **Password hashing is correct** — per-password `gensalt()`, cost 12, `checkpw` — apart from the 72-byte ceiling in P1-8.
- **`vite.config.js` is clean** — no proxy, no `0.0.0.0` host, no `define` leaks, no production sourcemaps.
- **`backend/docs/openapi.json` is NOT stale** — diffed against live `app.openapi()`, 0 differing lines.
- **The misspelled filenames are safe** — every reference matches the on-disk name character-for-character, so the misspelling is internally consistent and Linux resolves it identically. **No deploy risk**; cosmetic only (and fixed on the cleanup branch).
- **No phantom imports in either ecosystem.** `python-multipart` correctly absent (JSON-only app). 5 benign lockfile duplicates, none vulnerable.
- **Test-suite key fixtures are synthetic** (`"sk-test-key"`, `"fake-token"`) and all provider calls in tests are mocked — nothing to rotate.

---

# Nothing executes AI-generated output today

Stated plainly because it was the explicit concern: **the current attack surface for generated code is zero.**

Backend greps for `eval(` / `exec(` / `subprocess` / `os.system` / `popen` / `compile(` / `pickle` / `importlib` / `__import__` / `shell=True` / `yaml.load` / `marshal` returned three hits, **all false positives**: a static SQL `text()` at `main.py:16`, a `re.compile` of a literal at `routes_auth.py:11`, and a test merely *named* `test_hash_is_not_plaintext`. Frontend greps returned zero.

Model output's only path is: SDK → string → JSON → React state → escaped `<pre>` / clipboard / text Blob / opaque DB column.

**Vocabulary warning for Phase 2 planning:** "execute" in this codebase means "call an LLM API" (`/api/execute`, `executeApi.js`, `test_execute.py`). That collides directly with the sandboxed-code-execution feature. **Rename one of them before writing the spec**, or the ambiguity will propagate into route names, tests, and docs.

Design requirements for the planned sandbox are in [AUDIT_SECURITY.md](AUDIT_SECURITY.md) — summarized: a real isolation boundary (gVisor/Firecracker/managed; `exec()` with restricted builtins is **not** a sandbox), one throwaway instance per execution, **default-deny egress with instance-metadata IPs and RFC1918 explicitly blocked** (this matters more here than in most products, because users paste live provider keys into this app), no host filesystem mount, runtime-enforced limits (wall clock, CPU, memory OOM, `pids-limit`, output bytes, concurrency), auth and metering from day one, treating sandbox output as untrusted *again* on the way back, and per-execution audit logs.

---

# Phase 2 readiness notes

Not backlog items — inputs to the spec, drawn from what the code actually supports today.

- **Output diffing is a small lift.** `DiffView.jsx` already implements working, tested word-level LCS — it is simply pointed at `versionA.prompt_text` vs `versionB.prompt_text` (`:51`). The two models' responses render side-by-side **un-diffed** (`:68-73`, `:88-93`), and the data needed is already sitting in `results[]`, unused. Retargeting the existing component is most of the feature.
- **Cost estimation is blocked upstream.** All three providers **actively discard the SDK `usage` object** (`openai_provider.py:38`, `anthropic_provider.py:31-37`, `gemini_provider.py:37`). Only latency is captured, and `PromptVersion` has no token or cost columns. Capture usage *before* building the estimator.
- **The "community library" is greenfield, not an extension.** `Template` has only id/name/category/content — no owner, author, visibility, or votes. Routes are GET-only and unauthenticated, and `test_templates.py:52-54` explicitly pins "no auth required." **Users cannot create or share templates at any privilege level.** Content is 11 hardcoded templates inserted by a manual script — a read-only, developer-curated global catalog, identical for every user. The one user-owned entity (`PromptVersion`) is strictly private with no sharing mechanism. Sharing, ownership, and moderation are all net-new.
- **Ollama has a test actively pinning its rejection** — `test_execute.py:136-140` asserts `"llama-3"` → 400. Model allowlists are duplicated in three places (consolidated by the cleanup branch's `supported_models.py`, which is the natural extension point).
- **OAuth is fully net-new** — no library, no routes, no columns, no callback handling.

---

# Suggested execution order

1. **P0-1** — rotate the JWT secret, require the env var, strip it from the README *(hours)*
2. **P0-2** — isolate the test database *(hours; must precede any Postgres work)*
3. **P0-3** — auth + rate limits + input bounds on the three LLM endpoints *(a day)*
4. **P2-1** — land `cleanup/codebase`, which clears P1-7 and part of P1-9 *(review-bound)*
5. **P1-2, P1-3, P1-8, P1-10** — the four real user-facing bugs *(under a day together)*
6. **P1-4, P1-5, P1-6** — in-range security patches and the two free dependency deletions *(hours)*
7. **P1-1 + P1-11** — Postgres driver, Alembic, migration; regenerate `requirements.txt` from a real manifest *(the largest infra item)*
8. **P2-2** — fix the ESLint config, then gate CI on green tests + zero warnings
9. Remaining P2, then **P1-12 / P2-14** majors on their own branches with tests green first
10. Phase 2 spec — starting with the naming collision and the `usage`-capture prerequisite

Steps 1–5 are roughly two focused days and take the repo from *a forgeable auth secret, three open endpoints, a destructive test suite, 4 failing tests, and 118 lint errors* to green, safe to run, and ready to build on.
