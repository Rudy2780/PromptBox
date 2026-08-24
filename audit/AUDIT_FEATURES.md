# PromptBox — Feature Completeness Audit

**Audited commit:** `2dc37bb` (Initial commit), branch `main`
**Method:** every source file in `backend/app`, `backend/tests`, `frontend/src` read end to end (~4,600 lines total, excluding `node_modules` and generated `docs/`). `backend/docs/openapi.json` and both test suites used as corroboration. Keyword searches used only to prove absence.

> **Bottom line:** The repo is a *working, well-tested prompt-engineering workbench* — multi-model execution, version control, diffing, export, key validation. It is **not** mid-pivot to a code-generation evaluation platform: not one line of code exists for sandboxed execution, rubric grading, or Ollama. Several items on the "planned" list (side-by-side model comparison, diffing) are **already built** for prose output.

---

## Summary status table

| # | Feature (as described by owner) | Status | One-line reality |
|---|---|---|---|
| 1 | OAuth (GitHub + Google) | **NOT STARTED** | Zero OAuth code. Auth is email + password (bcrypt) → JWT HS256, 24h. |
| 2 | Prompt editor | **FULLY WIRED** | 62-line textarea + Execute → `POST /api/prompt`. |
| 2b | Live prompt scoring | **NOT STARTED** | No scoring/rubric/quality/lint code anywhere. |
| 3 | Auto-improve (3 variants) | **NOT STARTED** | No `improve`/`variant`/`refine`/`suggest` match in the repo. |
| 4 | Cost estimate | **NOT STARTED** | No cost/pricing/token-usage code. Providers discard usage data; only latency is captured. |
| 5 | Prompt chains | **NOT STARTED** | Execution is strictly single-turn. Only match for "chain" is a template *name*. |
| 6 | Community library | **NOT STARTED (as community)** | What exists is a **read-only global catalog of 11 hardcoded templates**. No user submissions, no ownership, no sharing. |
| 7a | Code diffing | **PARTIAL — but it's prompt-text diffing, not code diffing** | Word-level LCS over two saved *prompt versions*. Responses shown side-by-side un-diffed. |
| 7b | Sandboxed execution of generated code | **NOT STARTED** | No sandbox/docker/subprocess/exec. "Execute" = call an LLM API. |
| 7c | Rubric-based grading | **NOT STARTED** | No matches. |
| 7d | Ollama support | **NOT STARTED** | No matches. Hardcoded allowlists cover only OpenAI/Anthropic/Gemini cloud models. |
| 7e | Side-by-side model comparison | **FULLY WIRED (already done)** | Listed as "planned" but shipped: `POST /api/prompt` + checkbox multi-select + response grid. |
| 8a | Version CRUD + search | **FULLY WIRED** | Not mentioned by owner. 5 endpoints, user-scoped, debounced search, inline edit, delete. |
| 8b | Export (txt/md/json) | **FULLY WIRED** | Not mentioned by owner. |
| 8c | API key validation | **FULLY WIRED** | Not mentioned by owner. Gates the Execute button. |

### Stack claims vs. reality

| Claim | Reality |
|---|---|
| PostgreSQL | **False.** SQLite. `config.py:7` defaults to `sqlite:///./promptbox.db`; README:50, 93, 180 all say SQLite. **`requirements.txt` contains no Postgres driver at all** (no `psycopg2`, `asyncpg`, `pg8000`) — so even setting `DATABASE_URL` to a Postgres URL on Render would crash `create_engine` at import time. |
| React + Vite frontend | **True.** React 19.2, Vite 7.3 (`frontend/package.json:15-17, 31`). |
| FastAPI backend | **True.** FastAPI 0.135.1 (`requirements.txt:16`), `backend/app/main.py:20`. |
| Deployed on Vercel + Render | **Partly true — URLs only, no config in repo.** `main.py:24` allows origin `https://prompt-box-seven.vercel.app`; six frontend files hardcode `https://promptbox-9d83.onrender.com`. But there is **no `vercel.json`, `render.yaml`, `Dockerfile`, `Procfile`, or CI config** anywhere in the repo. |
| GitHub/Google OAuth | **False.** See §1. |
| Ollama support | **False.** See §7d. |

---

## 1. OAuth (GitHub + Google) — NOT STARTED

**Searched for and found zero matches** across `backend/app`, `backend/tests`, `frontend/src`, `README.md`, `requirements.txt`:
`oauth`, `OAuth`, `client_id`, `client_secret`, `redirect_uri`, `authlib`, `"Sign in with"`, `google_oauth`. `requirements.txt` contains **no** `authlib`, `httpx-oauth`, `requests-oauthlib`, `itsdangerous`, or session middleware. The only `github` match in the repo is the clone URL at `README.md:83`. The only `google` matches are the **Gemini SDK** (`google-genai`, `gemini_provider.py:7`) — a model provider, unrelated to sign-in.

### What auth actually exists — email + password + JWT (fully wired)

| Layer | File:line | Behavior |
|---|---|---|
| Password hashing | `backend/app/utils/security.py:4-8` | `bcrypt.hashpw` / `bcrypt.checkpw`. Real, correct. |
| User model | `backend/app/models/user.py:5-12` | `users` table: `id`, `email` (unique), `hashed_password`, `created_at`. **No `name`, no `provider`, no `oauth_id` column.** |
| Register | `backend/app/api/routes_auth.py:21-27` | Validates email regex + ≥8 char password (`:14-18`), 409 on duplicate, creates user. |
| Login | `backend/app/api/routes_auth.py:30-39` | Verifies password, returns `{status, token, email}`. |
| Token issue | `backend/app/services/auth_service.py:20-25` | `jose.jwt.encode`, HS256, `sub` = user id, `exp` = +24h. |
| Token verify | `backend/app/dependencies/auth.py:12-38` | `HTTPBearer` → decode → load user → 401 on failure. Used by all `/api/versions/*` and `/api/export/*` routes. |
| Frontend | `frontend/src/components/Login.jsx:46-63` | Picks `/auth/register` or `/auth/login`, POSTs `{email, password}`, calls `onAuth({email, token})`. |

**Tests:** `backend/tests/test_auth.py` (8 tests: register/duplicate/short-password/bad-email/login/wrong-password/nonexistent/JWT-claims), `test_security.py` (3), `frontend/src/test/login.test.jsx`, `register.test.jsx`.

### Defects found in the auth path

- **"Name" field is UI-only.** `Login.jsx:92-97` renders a Name input bound to `form.name`, but the request body at `:51` sends only `{email, password}`, and `UserInfo` has no name column. The value is collected and silently discarded.
- **"Continue as Guest" is a half-feature.** `Login.jsx:71-74` calls `onAuth(null)`. `App.jsx:19` gates on `user !== undefined`, so `null` passes and the Dashboard renders — but every `{user && …}` block inside `dashboard.jsx` (`:92`, `:101`, `:106`, `:113`) is falsy, so a guest gets model selection + prompt execution + responses, and silently **no** Save/Export/Versions/Compare panels. No message explains why.
- **No session persistence.** `grep localStorage|sessionStorage frontend/src` → **no matches**. The token lives only in `App.jsx:8` React state, so a page refresh logs the user out.
- **`JWT_SECRET` defaults to `"dev-secret-change-me"`** (`config.py:8`) — if unset on Render, every token is forgeable.

---

## 2. Prompt editor — FULLY WIRED · Live prompt scoring — NOT STARTED

### Editor (wired end to end)

`frontend/src/components/PromptEditor.jsx` is 62 lines total: a labelled `<textarea>` (`:50-56`) and an Execute button (`:57-59`). On submit (`:17-39`) it calls `executeBatch({prompt, models, apiKeys})` → `executeApi.js:46` → `POST /api/prompt` → `routes_execute.py:71-104` → real provider SDK call → results flow back to `dashboard.jsx:83` `setResults` → `ResponseDisplay`. Verified end to end.

The button is gated by `isDisabled` (`:41-45`): requires a validated API key, non-empty prompt, and ≥1 model.

### Scoring — does not exist

**Zero matches** for `score`, `scoring`, `rubric`, `grade`, `grading`, `quality`, `lint`, `evaluate` in the entire repo. There is no scoring service, no scoring endpoint (confirmed against the full 15-endpoint list in `backend/docs/openapi.json`), no score column on any model, and no scoring UI. The editor has **no** live analysis of any kind — no token count, no length warning, no variable/placeholder detection, no suggestions.

---

## 3. Auto-improve (3-variant generation) — NOT STARTED

**Zero matches** for `improve`, `variant`, `refine`, `suggest`, `rewrite`, `alternative`. No endpoint in `openapi.json`. Nothing in the codebase ever sends a prompt *about* a prompt — `routes_execute.py:60` and `:94` pass the user's raw prompt string straight through to the provider. There is no meta-prompting anywhere.

---

## 4. Cost estimate — NOT STARTED

**Zero matches** for `cost`, `pricing`, `usage`, `token_count`, `tokens`, `$`, `per_1k`. There is no price table for any model.

More telling: **the providers actively throw away the data a cost estimate would need.** All three read only the text out of the SDK response and discard the `usage` object the APIs return:
- `openai_provider.py:38` — `completion.choices[0].message.content` only
- `anthropic_provider.py:31-37` — iterates content blocks for the first text block only
- `gemini_provider.py:37` — `getattr(response, "text", None)` only

The only metric captured is wall-clock latency (`time.perf_counter()`, e.g. `openai_provider.py:28, 56`). The `PromptVersion` model (`models/prompt_version.py:17-19`) persists `response_text`, `response_model`, `response_latency` — **no token or cost columns**. `ExecuteResponse` (`schemas/execute_schema.py:11-14`) carries only `model`, `response_text`, `latency`.

---

## 5. Prompt chains — NOT STARTED

**One match for "chain" in the whole repo**, and it is a template *name*: `seed_templates.py:103` — `name="Few-Shot Chain-of-Thought"`. That is prompt-engineering terminology in seed content, not a chaining feature.

No matches for `pipeline`, `step`, `node`, `workflow`, `dag`. There is no chain model, no chain table, no chain endpoint in `openapi.json`, and no chain UI. The execution contract is rigidly single-turn: `ExecuteRequest` is one `prompt: str` (`execute_schema.py:5-8`), `LLMProvider.run_prompt(prompt)` returns one `(text, latency)` tuple (`llm_provider_base.py:5-7`), and there is no conversation/message-history parameter anywhere. `PromptBatchRequest` (`:17-21`) is *parallel fan-out to N models*, not sequential chaining.

---

## 6. Community library — NOT STARTED (as community). What exists is a read-only seeded global catalog.

**This is the most important distinction in the audit.** Being precise about all three possibilities:

| | Exists? | Evidence |
|---|---|---|
| **Community / shared** (users publish templates others can browse) | **NO** | No `user_id`/`author`/`is_public`/`votes` column on `Template`; no write endpoints; zero matches for `community`, `public`, `shared`, `fork`, `upvote`, `favorite`. |
| **Personal** (each user has their own templates) | **NO** | `Template` has no owner column at all; `/api/templates/` requires no auth and returns the same rows to everyone. |
| **Seeded global catalog** (one fixed list for all users) | **YES** | This is what is built. |

### The template system, precisely

- **Model** — `backend/app/models/template.py:4-12`. Columns are **only** `id`, `name`, `category`, `content`. No `user_id`, no author, no visibility flag, no vote count, no `created_at`.
- **Endpoints** — `backend/app/api/routes_templates.py`: `GET /api/templates/` with optional `?category=` filter (`:20-28`) and `GET /api/templates/{id}` (`:30-37`). **That is all — no POST, PUT, PATCH, or DELETE.** Confirmed against `backend/docs/openapi.json`: templates appear only as two GETs. **Users cannot create, edit, share, or delete templates through the application at any privilege level.**
- **No authentication** — neither route uses `Depends(get_current_user)`. `backend/tests/test_templates.py:52-54` explicitly asserts `test_get_templates_no_auth_required`. The catalog is world-readable on the public Render URL.
- **Content is hardcoded by the developers** — `backend/app/seed_templates.py:13-175` is a literal Python list of **11 templates** in 3 categories: `reasoning` (4), `structure` (4), `task` (3). Inserted by a manually-run script (`python -m app.seed_templates`, README:182), guarded by an idempotency check (`:8-11`).
- **UI** — `frontend/src/components/TemplateLibrary.jsx` is genuinely wired: `getTemplates(cat)` on mount and on category change (`:11-27`), All/Reasoning/Structure/Task filter buttons (`:43-68`), and a nice confirm-before-overwrite guard (`:29-37`) before calling `onSelectTemplate(content)` → `dashboard.jsx:47-49` → `setPrompt`. Tested in `frontend/src/test/TemplateLibrary.test.jsx` (5 tests).

**Summary: it is a read-only, unauthenticated, developer-curated catalog of 11 prompt templates, identical for every user.** Turning it into a community library requires: an owner column + author attribution, write endpoints with auth, a visibility/moderation model, and probably voting/search — none of which exists.

### The user-owned thing that *does* exist is strictly private

`PromptVersion` is owned and isolated: every query filters on `PromptVersion.user_id == user.id` (`routes_versions.py:41, 59, 72-75, 92-95`; `routes_export.py:41-44`). `backend/tests/test_search.py:50-59` asserts one user cannot see another's versions. There is **no** mechanism to share, publish, or link a version to another user.

### Deployment risk found here

`backend/app/main.py:9` runs `Base.metadata.create_all(bind=ENGINE)` but the imports at `:4-5` cover only `user` and `prompt_version` — **the `template` model is never imported**, so the `templates` table is not created by app startup. It exists only if `seed_templates.py` (which calls `create_all` itself at `:5`) has been run first. On a fresh Render deploy without that manual step, `GET /api/templates/` raises on a missing table and the Template Library panel shows an error for every user. (Independently noted in `BUGS.md` on the `origin/cleanup/codebase` branch.)

The local `backend/promptbox.db` currently has **0 rows in all three tables** (`users` 0, `templates` 0, `prompt_versions` 0) — it is an empty, git-ignored dev artifact (`backend/.gitignore:1` `*.db`; not tracked by git).

---

## 7. Code-generation-evaluation work

### 7a. Code diffing — PARTIAL, and it is **prompt-text** diffing, not code-output diffing

`frontend/src/components/DiffView.jsx` implements a real diff algorithm — a word-level LCS dynamic-programming table (`:3-39`) producing `unchanged`/`removed`/`added` chunks, rendered as two columns with red/green highlighting (`:59-66`, `:79-86`). It works and is tested (`frontend/src/test/DiffView.test.jsx`, 5 tests).

**But what it diffs is the prompt, and the two things compared are two saved versions by the same user:**

- **`DiffView.jsx:51`** — `const diff = computeDiff(versionA.prompt_text, versionB.prompt_text)`. This is the single load-bearing line: the diff input is **`prompt_text`**, never `response_text`.
- Responses are rendered raw and **un-diffed**, one per column: `:68-73` (`versionA.response_text` in a plain `<p>`) and `:88-93`.
- Inputs come from `DiffVerisonPicker.jsx` (filename typo is in the repo), which loads the user's own saved versions via `getVersions(token)` (`:11`) and requires exactly two selections (`:26`, `:67`), sorted oldest-first (`:33-34`).

**Missing for code diffing:** line-based (not word-based) diffing, syntax highlighting, language awareness, and — most importantly — the ability to diff **two models' outputs against each other**, which is the natural code-eval use case. The data is right there (`results[]` holds N model responses side by side) but nothing diffs it. Splitting on `/\s+/` (`:4-5`) would also mangle code indentation.

### 7b. Sandboxed execution of generated code — NOT STARTED

**Zero matches** for `sandbox`, `docker`, `subprocess`, `os.system`, `exec(`, `eval(`, `pty`, `container`, `firejail`, `nsjail`. `requirements.txt` contains no execution/sandboxing dependency.

Worth stating plainly because the vocabulary collides: **"execute" in this codebase means "send a prompt to an LLM HTTP API."** `POST /api/execute` (`routes_execute.py:46-68`) and `ExecuteRequest`/`ExecuteResponse` are about LLM calls. No generated code is ever run, parsed, compiled, or tested.

### 7c. Rubric-based grading — NOT STARTED

**Zero matches** for `rubric`, `grade`, `grading`, `criteria`, `judge`, `evaluat*`, `score`. No grading model, endpoint, or UI. Nothing in the repo passes a model's output back to a model for assessment.

### 7d. Ollama support — NOT STARTED

**Zero matches** for `ollama` or `11434`. `backend/app/providers/` contains exactly three concrete providers — `openai_provider.py`, `gemini_provider.py`, `anthropic_provider.py` — all cloud SDK wrappers requiring a user-supplied API key. There is no local/self-hosted provider and no base-URL override.

Adding Ollama also means editing a model allowlist duplicated in **three** places, all of which reject unknown models:
- `routes_execute.py:16-23` → unknown model raises 400 (`:33`, `:43`)
- `routes_validate_key.py:7-22` → unknown provider raises 400 (`:30-31`)
- `frontend/src/components/ModelSelector.jsx:4-8` (frontend's own hardcoded copy)

`backend/tests/test_execute.py:136-140` explicitly asserts that `"llama-3"` returns **400 Unsupported model** — i.e. the current behavior of rejecting local models is pinned by a passing test.

### 7e. Side-by-side multi-model comparison — ALREADY FULLY WIRED

The owner lists this as *planned*. It is **built and tested**. See §8a.

---

## 8. What's actually built (the owner's stale mental model)

### 8a. Multi-model side-by-side execution — FULLY WIRED
- **Backend:** `POST /api/prompt` (`routes_execute.py:71-104`) accepts `{prompt, models[], api_keys{provider→key}}`, resolves each model to a provider (`:36-43`), picks the matching key with single-key fallback (`:86`), executes each, returns `{responses: [{model, response_text, latency}]}`. Providers can be freely mixed in one request.
- **Frontend:** `ModelSelector.jsx:112-129` renders checkboxes for all 8 models grouped by provider (mix freely, min-one-selected enforced at `:38-40`); `executeApi.js:46-67` posts the batch; `ResponseDisplay.jsx:37-48` renders a card grid with model name, `<pre>` response, latency, plus Copy and client-side Export buttons (`:17-35`).
- **Tests:** `frontend/src/test/MultiModelPrompt.test.jsx` (3 tests), `backend/tests/test_prompt_batch.py` (3 tests).

### 8b. Prompt version control — FULLY WIRED
Full CRUD, all auth-gated and user-scoped: `POST /` (`routes_versions.py:14-33`), `GET /` with search (`:35-51`), `GET /{id}` (`:53-62`), `PATCH /{id}` (`:65-83`), `DELETE /{id}` (`:86-100`). Search is a case-insensitive `LIKE` over name **and** tag (`:43-49`).
UI: `SaveVersion.jsx` (name, optional tag, "include response" checkbox `:54-62`), `VersionSelector.jsx` (list, 300 ms debounced search `:32-35`, inline rename/retag `:55-83`, delete with in-flight state `:85-102`). Loading a version repopulates the editor **and** the response pane (`dashboard.jsx:25-39`).
Tests: `test_versions.py` (14), `test_search.py` (4), `VersionSelector.test.jsx` (9), `SaveVersion.test.jsx` (2).

### 8c. Export — FULLY WIRED
`GET /api/export/{version_id}?format=txt|md|json` (`routes_export.py:34-77`) with hand-written `txt` (`:12-20`) and Markdown (`:22-32`) serializers, auth + ownership check (`:41-44`), and `Content-Disposition: attachment` (`:73-77`). UI: `ExportDropdown.jsx` + `exportApi.js:42-55` blob-download with filename parsed from the header (`:36-40`). Tests: `test_export.py` (5), `ExportDropdown.test.jsx` (5).

### 8d. API key validation — FULLY WIRED
`POST /api/validate-key` (`routes_validate_key.py:28-41`) → `llm_service.test_provider_key` (`:18-30`) makes a real cheap call per provider (`models.list()` for OpenAI/Gemini, a 1-token message for Anthropic). UI: `ModelSelector.jsx:56-76` validates **every selected provider in parallel** via `Promise.all` and only reports success if all pass; the result gates the Execute button (`dashboard.jsx:76` → `PromptEditor.jsx:42`). Tests: `test_validate_key.py` (4), `ModelSelector.test.jsx` (3).

### 8e. Also present
Three provider adapters with error→HTTP mapping (`ProviderAuthError`→401, `ProviderError`→502, `routes_execute.py:61-66`); health endpoints (`routes_health.py`, `main.py:32-34`); a static OpenAPI spec (`backend/docs/openapi.json`, 15 endpoints); pre-generated JSDoc HTML in `frontend/docs/`. **10 backend pytest files and 17 frontend vitest files** — test coverage is genuinely the strongest part of this repo.

---

## Explicitly flagged: UI-only, and backend-only

### UI that exists but has nothing behind it
| Item | Evidence |
|---|---|
| **`Navbar.jsx` is a 0-byte empty file** | `frontend/src/components/Navbar.jsx` — completely empty, and `grep -rn Navbar frontend/src` → **no matches**. Never imported. |
| **`ErrorMessage.jsx` is orphaned** | A real 12-line component (`:1-9`) imported by **nothing** except its own test. `dashboard.jsx:125` inlines its own `<p style={{color:"red"}}>{error}</p>` instead. |
| **Login "Name" field** | `Login.jsx:92-97` collects it; `:51` never sends it; no DB column. Pure decoration. |
| **`ResponseDisplay` "Export" button** | `:24` → `exportText` (`:7-15`) is a client-side `Blob` download. Unrelated to the backend export endpoint — the two exports don't share code or format. |

### Backend endpoints with no UI calling them
| Endpoint | Evidence |
|---|---|
| **`GET /api/versions/{id}`** | Backend `routes_versions.py:53-62` and client helper `versionsApi.js:70` exist and are tested, but **no component imports `getVersion`**. Components use the list response directly. |
| **`GET /api/templates/{id}`** | `routes_templates.py:30-37` + `templatesApi.js:30` — **no component imports `getTemplate`**. |
| **`POST /api/execute` (single-model)** | Fully implemented (`routes_execute.py:46-68`) and tested (10 tests). In the running app it is **unreachable**: `PromptEditor.jsx:29` calls it only on the legacy `model` prop branch, and `dashboard.jsx:79-87` always passes `models` (array), so `hasModels` at `:21` is always true. Exercised only by tests. |
| **`GET /health/`** | `client.js:8` `getHealth` is defined and unit-tested but called by no component. |

---

## Bugs and risks found while reading

1. **`anthropic_provider.py:42` raises `ProviderAuthError` for *every* exception** (`raise ProviderAuthError(f"Anthropic provider error: {exc}")`) — the generic branch should raise `ProviderError`. Consequence: any Anthropic failure (rate limit, network, bad model id) surfaces to the user as **401 "invalid API key."** OpenAI (`:54`) and Gemini (`:47`) correctly raise `ProviderError` → 502. Also flagged in `BUGS.md` on `origin/cleanup/codebase`.
2. **`llm_service.py` defines `test_anthropic_key` twice** — `:40-50` and again `:60-74`. Python silently keeps the second; the first is dead code. The two use different models (`claude-sonnet-4-20250514` vs `claude-haiku-4-5-20251001`) and different error handling, so the dead copy is misleading.
3. **`/api/execute` and `/api/prompt` require no authentication** (`routes_execute.py:46, 71` — no `Depends(get_current_user)`). Anyone can POST to the public Render URL. The caller supplies their own key so there's no key theft, but there is no rate limiting or abuse control on a public endpoint that makes outbound paid API calls.
4. **`main.py:11-18` is a hand-rolled migration** — inspects for the `tag` column and issues a raw `ALTER TABLE` at import time. No Alembic. It will not scale past this one column, and it runs on every boot.
5. **`main.py:9` `create_all` omits the `template` model** — see §6, deployment-order risk.
6. **`API_BASE` is hardcoded to the Render URL in six files** (`client.js:1`, `executeApi.js:1`, `exportApi.js:1`, `templatesApi.js:1`, `versionsApi.js:1`, `Login.jsx:8`). No env var, so `npm run dev` talks to **production**, and local backend development requires editing six files. (The `origin/cleanup/codebase` branch fixes this with `src/api/config.js`.)
7. **The model list is duplicated in three places** that must be kept in sync by hand — `routes_execute.py:16-23`, `routes_validate_key.py:7-22`, `ModelSelector.jsx:4-8`.
8. **API keys live in React state and are re-sent in the plaintext body on every execution** (`executeApi.js:54`). Never persisted server-side — arguably intentional (README:102) — but they're also lost on refresh, forcing re-entry and re-validation each session.
9. **Filename typos committed:** `DiffVerisonPicker.jsx` and `test/vesrionsApi.test.js`. Both fixed on `origin/cleanup/codebase`.
10. **`ModelSelector.jsx` and `PromptEditor.jsx` carry dual legacy/modern prop paths** (`ModelSelector.jsx:22-28, 82-110`; `PromptEditor.jsx:5-13`) kept alive only for older tests. The legacy branches are dead in the real app and roughly double the components' branching.

### Note on the other branch
`origin/cleanup/codebase` exists and is **refactor-only — it adds no features.** It extracts `supported_models.py` and `version_service.py`, adds `frontend/src/api/config.js`, fixes the two filename typos, renames `dashboard.jsx`→`Dashboard.jsx`, deletes the empty `Navbar.jsx`, and adds `BUGS.md` (2 known bugs, both independently confirmed above). Nothing on that branch touches OAuth, scoring, cost, chains, sandboxing, grading, or Ollama.
