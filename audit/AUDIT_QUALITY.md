# PromptBox — Code Quality & Dead Code Audit

**Date:** 2026-08-24 · **Commit:** `2dc37bb` (Initial commit, clean tree) · **Scope:** `backend/`, `frontend/` (excl. `node_modules`, `__pycache__`, `dist`)

**Ratings** are *effort-to-impact*: **HIGH** = large payoff for small effort (do first) · **MEDIUM** = worth doing · **LOW** = cosmetic or high-cost/low-payoff.

---

## Verdict on the "mid-pivot" premise

**The pivot has not started in the code.** Grep across all `*.py`, `*.js`, `*.jsx`, `*.md`, `*.json` for `codegen`, `evaluat*`, `rubric`, `judge`, `scorecard`, `leaderboard`, `benchmark`, `pass@` returns **zero** hits in source. There is no sandboxed execution, no grading model, no evaluation schema, no evaluation route. Every backend route in `router.py` and every mounted frontend component serves the original prompt-management product.

**So the dead code in this repo is not pivot residue.** It is ordinary accretion, and it has three distinct sources, each of which explains a cluster of findings:

1. **An `API_BASE` find-and-replace that missed three targets** (§4.1) — the single root cause of all 4 failing frontend tests *and* the stale `frontend/docs/`.
2. **A `ModelSelector`/`PromptEditor` single→multi-model refactor that kept both branches alive** "for backward compatibility & tests" (`ModelSelector.jsx:22`) — the legacy branches are unreachable in the running app.
3. **A template-category rename** (`structural`/`use_case` → `reasoning`/`structure`/`task`) applied to the seed data and the component but **not** to the CSS or the test fixtures (§2.4).

---

## Summary table

| # | Finding | Evidence | Rating |
|---|---|---|---|
| 1 | `AnthropicProvider` raises `ProviderAuthError` for *every* failure → all Anthropic errors become **401** | `anthropic_provider.py:42` | **HIGH** |
| 2 | `ModelSelector.handleValidate` has no `try/catch` → network failure permanently sticks the button on "Validating…" | `ModelSelector.jsx:56-76` | **HIGH** |
| 3 | `test_anthropic_key` **defined twice**; first definition (lines 40-50) is silently shadowed and dead | `llm_service.py:40-50` vs `:60-74` | **HIGH** |
| 4 | `API_BASE` hardcoded in **6 files**; drift causes 4 failing tests + stale JSDoc | `client.js:1`, `executeApi.js:1`, `exportApi.js:1`, `templatesApi.js:1`, `versionsApi.js:1`, `Login.jsx:8` | **HIGH** |
| 5 | 4 frontend tests **failing** on `main` | `api.client.test.js`, `executeApi.test.js`, `vesrionsApi.test.js` | **HIGH** |
| 6 | ESLint: **118 problems** (114 errors) — 107 are `no-undef` from missing vitest globals in eslint config | `eslint.config.js:16-24` | **HIGH** |
| 7 | Backend tests wipe the **real** `promptbox.db`; no test-DB isolation | `conftest.py:8-21` | **HIGH** |
| 8 | `Login.jsx` `loading` state set but never consumed → double-submit possible | `Login.jsx:15,45,67` | **HIGH** |
| 9 | Auth token in React state only, no persistence → hard refresh logs user out | no `localStorage` anywhere in `src/` | MEDIUM |
| 10 | `Content-Disposition` not in CORS `expose_headers` → export filename always falls back | `main.py:22-28` vs `exportApi.js:36` | MEDIUM |
| 11 | `routes_auth._validate()` duplicates Pydantic validation and is unreachable | `routes_auth.py:14-18`, proven by `test_auth.py:27,35` | MEDIUM |
| 12 | `TemplateResponse.model_config` is dedented to module scope — config never applied | `routes_templates.py:18` | MEDIUM |
| 13 | Template category CSS targets the **old** vocabulary → badges render unstyled | `TemplateLibrary.css:65-73` vs `seed_templates.py` | MEDIUM |
| 14 | `validate-key` returns **401 "Invalid API key"** for network/quota errors too | `llm_service.py:29-30` → `routes_validate_key.py:38` | MEDIUM |
| 15 | Legacy single-model branches in `ModelSelector`/`PromptEditor` are dead in-app | `ModelSelector.jsx:82-110`, `PromptEditor.jsx:28-30` | MEDIUM |
| 16 | Three separate test files test `Login.jsx`; ~4 assertions triplicated; one is in the wrong directory | `components/Login.test.jsx`, `test/login.test.jsx`, `test/register.test.jsx` | MEDIUM |
| 17 | `frontend/docs/` stale + **unregeneratable** (no jsdoc dep, no script, no config) | `package.json:19-33` | MEDIUM |
| 18 | `computeDiff` is uncapped O(n·m) LCS → freezes on large prompts | `DiffView.jsx:3-39` | MEDIUM |
| 19 | Dead files: `Navbar.jsx` (0 bytes), `user_schema.py` (0 bytes), `llm_provider_base.py`, `react.svg` | see §1 | MEDIUM |
| 20 | Unused exports: `getTemplate`, `getVersion`, `getHealth` | `templatesApi.js:30`, `versionsApi.js:70`, `client.js:8` | MEDIUM |
| 21 | Model catalog duplicated in **3** places, drifting | `ModelSelector.jsx:4-8`, `routes_validate_key.py:7-22`, `routes_execute.py:16-23` | MEDIUM |
| 22 | `llm_service.py` imports SDKs unguarded, unlike `providers/` → missing SDK crashes app boot | `llm_service.py:14-16` | MEDIUM |
| 23 | `DiffView` "blocked" branch is unreachable and its message is wrong | `DiffView.jsx:43-49` | LOW |
| 24 | `VersionSelector.loadVersions` early-returns leaving `loading=true` forever | `VersionSelector.jsx:19` | LOW |
| 25 | Duplicated `<select>` chevron CSS block | `App.css:216-229` vs `ExportDropdown.css:18-31` | LOW |
| 26 | Dead CSS: `.validation-success`, `.validation-error`, `.structural`, `.use_case` | `App.css:279-289`, `TemplateLibrary.css:65-73` | LOW |
| 27 | Missing CSS: `.sr-only`, `.diff-picker`, `.diff-text`, `.textarea` used but never defined | see §2.4 | LOW |
| 28 | README contradicts the code on the backend URL | `README.md:155` | LOW |
| 29 | `datetime.utcnow()` deprecated — 67 warnings in the pytest run | `user.py:12`, `prompt_version.py:21`, `auth_service.py:23` | LOW |

**Clean results worth stating:**

- **Zero** `TODO` / `FIXME` / `HACK` / `XXX` / `BUG` markers repo-wide.
- **Zero** unresolved merge-conflict markers.
- **Zero** mutable default arguments in Python.
- Every list render has a `key` prop.
- `backend/docs/openapi.json` is **exactly current** — 0 differing lines vs. `app.openapi()` (verified programmatically).
- The misspelled filenames are **safe** — see §3.6.

---

## 1. Dead / unused code

### 1.1 Import graph (built by grepping every `import`/`require`/`vi.mock` in `frontend/src`)

`main.jsx` → `App.jsx` → { `pages/dashboard.jsx`, `components/Login.jsx` }
`dashboard.jsx` → `ModelSelector`, `PromptEditor`, `ResponseDisplay`, `SaveVersion`, `VersionSelector`, `DiffVerisonPicker`, `DiffView`, `ExportDropdown`, `TemplateLibrary` — **all 9 reachable**.

### 1.2 Definitely dead — safe to delete

| File | Evidence | Rating |
|---|---|---|
| `frontend/src/components/Navbar.jsx` | **0 bytes**. `grep -rn "Navbar" src/` → zero hits. | **HIGH** |
| `backend/app/schemas/user_schema.py` | **0 bytes**. `grep -rn "user_schema"` → zero hits. | **HIGH** |
| `backend/app/providers/llm_provider_base.py` | `grep -rn "LLMProvider\|llm_provider_base"` matches **only its own definition**. No provider subclasses it, and its `async def run_prompt` (`:6`) contradicts the three concrete providers, which are all **sync**. It is not just unused — it is actively misleading about the interface. | MEDIUM |
| `frontend/src/assets/react.svg` | Zero references. (`vite.svg` **is** used — `index.html:5`.) | MEDIUM |
| `backend/app/services/llm_service.py:40-50` | `test_anthropic_key` is redefined at `:60-74`; Python keeps the **second**. The first, which pins `claude-sonnet-4-20250514`, is unreachable. See §1.5. | **HIGH** |

**`person.png`, `email.png`, `password.png` are all used** — `Login.jsx:4-6`. Do not delete.

### 1.3 Unused exports — verify first

| Export | Status | Rating |
|---|---|---|
| `templatesApi.js:30` `getTemplate(id)` | **Zero** callers. Backs a real, tested endpoint (`routes_templates.py:30`) with no UI consumer. | MEDIUM |
| `versionsApi.js:70` `getVersion(token, id)` | **Zero** callers. Same shape — endpoint exists (`routes_versions.py:53`), no consumer. | MEDIUM |
| `client.js:8` `getHealth()` | Only caller is `test/api.client.test.js` — a test that currently **fails**. Nothing in the app surfaces health. | MEDIUM |

All three back live endpoints. Either delete the client wrapper and its endpoint, or wire them up (a "server waking up…" indicator using `getHealth` would be genuinely useful on Render's free tier — see §4.2). **Do not delete `executePrompt`**: it is reachable via `PromptEditor.jsx:29`, just not from the current dashboard.

### 1.4 Unreferenced components

`ErrorMessage.jsx` is imported **only** by `test/ErrorMessage.test.jsx`. The dashboard renders errors inline instead (`dashboard.jsx:125`: `{error && <p style={{color:"red"}}>{error}</p>}`), and `App.css:` already defines `.error-message`, which only `ErrorMessage.jsx:5` uses.

**Action:** use it — replace `dashboard.jsx:125` with `<ErrorMessage message={error} />`. It is strictly better than the inline version (adds `role="alert"`). This deletes an inline style, revives a dead component, and gives `.error-message` a real consumer. **MEDIUM.**

### 1.5 Backend dead code

**Duplicate function definition — `llm_service.py`.** `test_anthropic_key` is defined at `:40-50` and again at `:60-74`. Only the second survives. They differ meaningfully:

```
:40-50  model="claude-sonnet-4-20250514", except AuthenticationError → False        [DEAD]
:60-74  model="claude-haiku-4-5-20251001", except AuthenticationError → print+False [LIVE]
```

The live one also has `print()` debugging left in (`:70`, `:73`). **Delete `:40-50`; replace the `print`s with `logging`. HIGH.**

**Unused variable.** `llm_service.py:55` — `response = client.models.list()` assigns and never reads.

**`routes_auth._validate()` is unreachable** (`routes_auth.py:14-18`). It re-checks email format and password length that `schemas/auth.py:3-5` already enforces via `EmailStr` and `Field(min_length=8)`. Pydantic runs **first** and returns **422**, so the function's `400` branches never fire. `test_auth.py:27` and `:35` confirm this — both assert **422**, not the 400 `_validate` would produce. **Verify first** (a hand-crafted address could in principle satisfy `EmailStr` but fail `EMAIL_RE`), then delete `EMAIL_RE`, `_validate`, and the two call sites. **MEDIUM.**

**No orphaned routes.** All 7 route modules are mounted in `router.py:13-19`. All 15 endpoints appear in the live OpenAPI schema.

### 1.6 Is `anthropic_provider.py` orphaned?

**No — it is fully wired.** `routes_execute.py:12` imports it and `:31-32` dispatches to it for the four `claude-*` models. Both `/api/execute` and `/api/prompt` reach it.

**But it is bypassed where you would expect it to be used.** `llm_service.py:60-74` constructs its own `anthropic.Anthropic(...)` client instead of reusing `AnthropicProvider` — as do the OpenAI and Gemini paths. So the repo has **two independent client-construction layers** per provider: `providers/*` for execution, `llm_service.py` for key validation. That is the duplication in §2.3.

There is **no `ModelSelector` in the backend** — that name belongs solely to the React component. The backend's equivalent is `routes_execute._get_provider` (`:26-33`).

### 1.7 Generated artifacts

**`backend/docs/openapi.json` — CURRENT, not stale.** Verified by importing `app.main` and diffing `app.openapi()` against the committed file: 15 endpoints each, identical path/method sets, identical schema sets, **0 differing JSON lines**. No action.

**`frontend/docs/` — STALE, in exactly one way.** I extracted the embedded `<pre class="prettyprint source">` block from each of the 5 generated pages and diffed against the current source. All five differ **only** on line 1:

```
-const API_BASE = "http://localhost:8000";
+const API_BASE = "https://promptbox-9d83.onrender.com";
```

Everything else — all 12 documented functions, every JSDoc block — matches current source. The docs were generated before the `API_BASE` change in §4.1.

Worse: **it cannot be regenerated.** `jsdoc` is not in `package.json` dependencies or devDependencies, there is no `docs` script, and there is no `jsdoc.json`/`.jsdoc.json` config. 32 files are committed (including ~18 webfont binaries) that no one can rebuild. `README.md:192` points reviewers straight at them.

**Action:** add `jsdoc` as a devDependency plus a `"docs": "jsdoc -r src/api -d docs"` script and regenerate; **or** delete `frontend/docs/`, gitignore it, and drop `README.md:192`. Either is fine — leaving it as-is is not. **MEDIUM.**

---

## 2. Duplicated logic

### 2.1 `API_BASE` — 6 copies (the highest-leverage fix in the repo)

```
api/client.js:1        const API_BASE = "https://promptbox-9d83.onrender.com";
api/executeApi.js:1    const API_BASE = "https://promptbox-9d83.onrender.com";
api/exportApi.js:1     const API_BASE = "https://promptbox-9d83.onrender.com";
api/templatesApi.js:1  const API_BASE = "https://promptbox-9d83.onrender.com"   ← no semicolon
api/versionsApi.js:1   const API_BASE = "https://promptbox-9d83.onrender.com";
components/Login.jsx:8 const API_BASE = "https://promptbox-9d83.onrender.com";
```

Six copies, one of them in a component. Someone changed the value from `http://localhost:8000` and updated all six — but not the **four test files** that assert on the old value, and not `frontend/docs/`. That single miss produces **all 4 test failures** (§5) *and* the entire staleness of `frontend/docs/` (§1.7) *and* the false statement at `README.md:155`.

**Fix:** one `src/api/config.js` exporting `export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000"`, imported by all six. Then the tests pass against the default, and prod is set via `.env.production`. This is the **single highest-value change in the audit. HIGH.**

### 2.2 Fetch/error-handling boilerplate — 5 near-identical blocks

`templatesApi.js:15-20`, `templatesApi.js:31-36`, `versionsApi.js:50-59`, `versionsApi.js:76-80`, `versionsApi.js:103-107` are all *literally* this:

```js
const res = await fetch(url, opts);
const data = await res.json();
if (!res.ok) throw new Error(data?.detail || "<message>");
return data;
```

`executeApi.js:26-33` and `:59-66` are the same shape with `data && data.detail ? data.detail : "…"` instead of `data?.detail || "…"` — a gratuitous third spelling. `saveVersion` (`versionsApi.js:27-34`) uses the same. `deleteVersion` (`:125-134`) and `downloadExport` (`:21-32`) need a variant because they have no JSON body on success.

**Consolidation:** a single `request(path, {method, token, body})` in `api/client.js` that centralizes base URL, `Content-Type`, `Authorization`, `res.ok` checking, and `detail` extraction. That removes ~60 lines across 5 files and, critically, gives you **one** place to add the missing 401-handling from §3.3. **HIGH.**

### 2.3 Provider adapter boilerplate — 3× at execution, 3× again at validation

`openai_provider.py`, `gemini_provider.py`, `anthropic_provider.py` share an identical skeleton: guarded SDK import → `__init__(api_key, model)` → `start = time.perf_counter()` → try SDK call → map auth error → `return str(content), float(latency)`. The timing and error-mapping scaffolding is ~15 duplicated lines per provider.

Then `llm_service.py:32-74` does it **all over again** for key validation, with a *different* import strategy (unguarded) and a *different* error policy. Six client-construction sites for three providers.

**Consolidation:** give `LLMProvider` (currently dead, `llm_provider_base.py`) a real `validate_key()` classmethod and a concrete `run_prompt` template method that owns timing and error mapping, leaving subclasses only `_call(prompt)`. Then have `llm_service.test_provider_key` dispatch through the same registry `routes_execute._get_provider` uses. This kills §1.2's dead base class *and* §2.3's duplication in one move. **MEDIUM.**

### 2.4 Duplicated & orphaned CSS

| Issue | Evidence | Rating |
|---|---|---|
| `<select>` chevron block duplicated | `App.css:216-229` (`.model-config select`) and `ExportDropdown.css:18-31` (`.export-container select`) share 11 of 13 declarations, including the **byte-identical inline SVG data-URI**. Extract a `.select-field` class. | LOW |
| `.version-date` defined twice | `DiffVersionPicker.css:41-44` and `VersionSelector.css` — identical intent. | LOW |
| `.error` defined twice | `ExportDropdown.css`, `VersionSelector.css`. | LOW |
| `.refresh-btn` borrowed across files | Used at `DiffVerisonPicker.jsx:41`, defined **only** in `VersionSelector.css`. Works because CSS is global; breaks silently if `VersionSelector` is ever removed. | LOW |
| **Dead category CSS** | `TemplateLibrary.css:65-73` styles `.template-category.structural` and `.template-category.use_case`. But `seed_templates.py` seeds **only** `reasoning` (×4), `structure` (×4), `task` (×3), and `TemplateLibrary.jsx:86` emits `` `template-category ${t.category}` ``. So the badges get **no** color, and 9 lines of CSS are dead. The old vocabulary survives in exactly one other place: the `test_templates.py:12-13` fixtures. | MEDIUM |
| Dead validation CSS | `App.css:279-289` `.validation-success` / `.validation-error` — zero JSX references. `ModelSelector.jsx:161-162` and `SaveVersion.jsx:66-67` use inline `style={{color:"green"}}` / `"red"` instead. Either adopt the classes or delete them. | LOW |
| **Missing CSS** | `.sr-only` (`ExportDropdown.jsx:33`) is defined **nowhere** — so the "Format" label meant to be screen-reader-only is **visibly rendered**. Also undefined: `.diff-picker` (`DiffVerisonPicker.jsx:38`), `.diff-text` (`DiffView.jsx:58,78`), `.textarea` (`PromptEditor.jsx:48`). | LOW |

> Note: `.org` and `.w3` appear as selectors to naïve regex scanning but are **false positives** — they come from `www.w3.org` inside the SVG data-URI. Not findings.

### 2.5 Duplicated test helpers

`register_and_get_headers(client, email, password)` is copy-pasted verbatim into `test_versions.py:7-11`, `test_export.py:7-11`, and `test_search.py:3-7`. `VALID_VERSION` is duplicated in `test_versions.py:13-17` and `test_export.py:13-19`. Both belong in `conftest.py` as fixtures. **MEDIUM.**

`test_prompt_batch.py:27-29` and `test_templates.py:19-21` each redefine a `client` fixture that `conftest.py:23-25` already provides. **LOW.**

---

## 3. Inconsistent patterns

### 3.1 camelCase / snake_case at the API boundary — half-translated

The api layer translates **requests** but passes **responses** through raw:

```js
executeApi.js:22  api_key: apiKey       // camelCase param → snake_case body
executeApi.js:55  api_keys: apiKeys     // translated
versionsApi.js:24 body: JSON.stringify(payload)   // NOT translated — caller must speak snake_case
```

So `SaveVersion.jsx:18-25` builds a raw snake_case object by hand, and snake_case leaks into JSX across **five** components: `dashboard.jsx` (`prompt_text`, `response_text`, `response_model`, `response_latency`), `DiffView.jsx` (`prompt_text` ×2, `response_text` ×4), `ResponseDisplay.jsx` (`response_text` ×3), `DiffVerisonPicker.jsx` (`created_at` ×3), `VersionSelector.jsx` (`created_at`).

**Pick one and hold it.** Cheapest: drop the partial translation, use snake_case end-to-end (matches the backend, matches most of what's already written). More correct: convert at the `api/` boundary only — which is trivial once §2.2's shared `request()` helper exists. **MEDIUM.**

### 3.2 Mixed API-calling styles

Everything goes through `api/*.js` **except auth**. `Login.jsx:48` calls `fetch()` directly with its own `API_BASE` (`:8`) and its own error-shape parser (`extractError`, `:22-27`). There is no `authApi.js`.

**Action:** create `api/authApi.js` with `register()` / `login()`. This removes the 6th `API_BASE` copy and puts `extractError` where the other four modules can use it — see §3.3. **MEDIUM.**

### 3.3 Inconsistent error shapes — the frontend only handles one of two

FastAPI returns **two different** error shapes:

- `HTTPException` → `{"detail": "some string"}`
- Pydantic 422 → `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`

`Login.jsx:22-27` handles both correctly via `extractError`, which unwraps arrays and objects. **Every other client does not:**

```js
versionsApi.js:57   throw new Error(data?.detail || "Failed to fetch versions");
executeApi.js:29    const detail = data && data.detail ? data.detail : "Execution failed.";
templatesApi.js:18  throw new Error(data?.detail || "Failed to fetch templates");
```

When a 422 comes back, `detail` is an **array**, and `new Error(array)` stringifies to `"[object Object]"` — which is exactly what `SaveVersion.jsx:67` renders to the user. This is reachable today: `VersionCreateRequest` enforces `name` max 255 and `tag` max 32 (`version_schema.py:5-6`), and `SaveVersion.jsx:41-46` puts **no `maxLength` on the name input** (it does on the tag, `:52`). Type a 256-character version name and the UI shows `[object Object]`. **MEDIUM.**

**Fix:** move `extractError` into the shared `request()` helper from §2.2 — one change fixes all five call sites.

Nothing anywhere handles **401**. When the 24-hour JWT (`auth_service.py:23`) expires, every authed call throws a raw string into a component-local error state and the user is never returned to login.

### 3.4 Mixed state management & async handling

All state is `useState` — no context, no reducer. Consistent, and fine at this size. But **prop-drilling is heavy**: `dashboard.jsx` holds 11 `useState` hooks and passes `user.token` separately to four children (`:94, :102, :108, :115`). A small `AuthContext` would also give §3.3's 401 handling somewhere to live. **LOW.**

Async handling is consistent *except in one place*, and that exception is a real bug:

| Component | Pattern |
|---|---|
| `SaveVersion.jsx:27-36` | `try / catch / finally` ✓ |
| `ExportDropdown.jsx:16-28` | `try / catch / finally` ✓ |
| `PromptEditor.jsx:24-38` | `try / catch / finally` ✓ |
| `VersionSelector.jsx:20-29, 68-82, 86-101` | `try / catch / finally` ✓ |
| `TemplateLibrary.jsx:12-22` | `try / catch / finally` ✓ |
| `DiffVerisonPicker.jsx:10-16` | `try / catch`, `console.error` only — error never surfaces to the user |
| **`ModelSelector.jsx:56-76`** | **no `try` at all** — see §4.2 |

### 3.5 File & export conventions

- **Exports:** mixed. `ErrorMessage.jsx:11` and `ResponseDisplay.jsx:50` use `function X(){}` + `export default X`; the other seven use `export default function X()`. `Login.jsx:10` uses `const Login = () => {}` + `export default`. **LOW.**
- **Component filenames:** all `PascalCase.jsx` **except** `pages/dashboard.jsx` (lowercase file, exports `DashBoard`, imported as `Dashboard` at `App.jsx:3`). Three different casings for one component. **LOW.**
- **Semicolons:** `DiffVerisonPicker.jsx`, `DiffView.jsx`, `TemplateLibrary.jsx`, `VersionSelector.jsx`, `templatesApi.js` omit them; everything else uses them. No Prettier config exists. **LOW.**
- **Quotes:** single in the four files above, double elsewhere. **LOW.**

### 3.6 The misspelled filenames — VERIFIED SAFE

This was flagged as a possible Linux-deploy breaker. **It is not.** Every reference matches the on-disk name **exactly**, character for character:

| On disk | Referenced as | Match? |
|---|---|---|
| `components/DiffVerisonPicker.jsx` | `dashboard.jsx:7` → `"../components/DiffVerisonPicker"` | ✅ exact |
| `components/DiffVerisonPicker.jsx` | `test/DiffVersionPicker.test.jsx:3` → `'../components/DiffVerisonPicker'` | ✅ exact |
| `components/DiffVersionPicker.css` | `DiffVerisonPicker.jsx:3` → `'./DiffVersionPicker.css'` | ✅ exact |
| `test/vesrionsApi.test.js` | — (matched by vitest's `*.test.js` glob) | ✅ runs |

The misspelling is **internally consistent**, so it resolves identically on case-sensitive filesystems. There is no deploy risk here. It is purely a readability wart — and a mildly confusing one, since the component file, its CSS, and its test file use two different spellings of the same word.

**Action:** rename `DiffVerisonPicker.jsx` → `DiffVersionPicker.jsx` and `vesrionsApi.test.js` → `versionsApi.test.js`, updating the 2 importers. Use `git mv` — on a case-insensitive macOS filesystem a plain rename that differs only in case can be missed by git, though here the letters differ, so a straight `git mv` is fine. **LOW** (cosmetic, but cheap).

### 3.7 Test conventions

Five inconsistencies in one suite:

1. **Location:** 17 test files in `src/test/`, but `components/Login.test.jsx` sits beside its component.
2. **Client construction (backend):** `test_execute.py:12` and `test_prompt_batch.py` build a module-level `TestClient(app)`; everything else uses the `client` fixture. The module-level client **bypasses `conftest.py`'s `clear_users` autouse fixture ordering**.
3. **Runner API:** `describe/it` in `SaveVersion.test.jsx`, `ErrorMessage.test.jsx`, `ResponseDisplay.test.jsx`; `describe/test` in `DiffView.test.jsx`, `VersionSelector.test.jsx`, `login.test.jsx`; bare top-level `test()` in `App.test.jsx`, `api.client.test.js`.
4. **Imports:** some files import `describe/it/expect/vi` from `vitest`, others rely on `globals: true` (`vite.config.js:9`). This split is what produces 107 of the 118 ESLint errors (§6).
5. **Mocking:** `vi.mock(path, factory)` in `TemplateLibrary.test.jsx:12`; bare `vi.mock(path)` automock in `SaveVersion.test.jsx:6`; `vi.spyOn` in `PromptEditor.test.jsx:16`; raw `global.fetch = vi.fn()` in `api.client.test.js:5`.

---

## 4. Bugs

### Markers sweep — clean

`grep -rnE "(^|[^A-Za-z])(TODO|FIXME|HACK|XXX|BUG)([^A-Za-z]|$)"` across the repo (excluding `node_modules`, `.git`, `__pycache__`, `dist`, `frontend/docs`, `package-lock.json`, `*.db`): **zero matches.**

`grep -rnE "^(<<<<<<< |>>>>>>> |=======$)"` over the same set: **zero matches.** No unresolved conflicts.

### 4.1 `AnthropicProvider` misclassifies every failure as an auth error — **HIGH**

`backend/app/providers/anthropic_provider.py:38-42`:

```python
except Exception as exc:
    auth_error_cls = getattr(anthropic, "AuthenticationError", None) if anthropic is not None else None
    if auth_error_cls is not None and isinstance(exc, auth_error_cls):
        raise ProviderAuthError("Invalid Anthropic API key") from exc
    raise ProviderAuthError(f"Anthropic provider error: {exc}") from exc   # ← should be ProviderError
```

The fallthrough on `:42` raises `ProviderAuthError` — the **auth** subclass. Compare the two sibling providers, which get it right:

- `openai_provider.py:54` → `raise ProviderError(f"OpenAI provider error: {exc}")`
- `gemini_provider.py:47` → `raise ProviderError(f"Gemini provider error: {exc}")`

`routes_execute.py:61-66` maps `ProviderAuthError` → **401** and `ProviderError` → **502**. So a rate limit, a network timeout, an overloaded model, or a typo'd model name on any Claude request is reported to the user as **"401 — invalid API key."** The user will rotate a perfectly good key.

**Fix:** change `ProviderAuthError` → `ProviderError` on `:42`. One word. There is **no Anthropic test in `test_execute.py`** to catch it — the file covers only OpenAI and Gemini.

### 4.2 `ModelSelector.handleValidate` — unhandled rejection deadlocks the button — **HIGH**

`frontend/src/components/ModelSelector.jsx:56-76`:

```js
const handleValidate = async () => {
  if (!selectedProviders.length) return;
  setLoading(true);
  setStatus(null);
  const results = await Promise.all(          // ← no try/catch
    selectedProviders.map((p) => { ... return validateKey(p, key).then(...); })
  );
  ...
  setLoading(false);                          // ← never reached on rejection
};
```

`validateKey` (`client.js:19-25`) has no error handling either — a rejected `fetch` propagates straight out. `Promise.all` rejects on the first failure, `handleValidate` throws, and **`setLoading(false)` never runs**. The button reads "Validating…" forever and is `disabled` (`:157`). The only recovery is a page reload — which, per §4.5, also logs the user out.

This is not a theoretical path. The backend is on Render's free tier, which cold-starts; the first `validateKey` after idle is *likely* to time out. And `isKeyValid` gates `PromptEditor`'s Execute button (`PromptEditor.jsx:42`), so the whole app is bricked until reload.

**Fix:** wrap in `try { … } catch { setStatus("invalid") } finally { setLoading(false) }` — matching the pattern the other six components already use (§3.4).

### 4.3 `Login.jsx` — `loading` computed but never used → double-submit — **HIGH**

`Login.jsx:15` declares `const [loading, setLoading] = useState(false)`. It is set at `:45` and cleared at `:67` — and **never read**. ESLint catches it: `Login.jsx:15:10  no-unused-vars  'loading' is assigned a value but never used`.

Consequence: the Sign Up / Login `<div>`s (`:124-137`) are never disabled and never show progress. They are `<div>`s with `onClick`, not `<button>`s, so there is no native disabled state either. Rapid clicks fire concurrent `POST /auth/register` calls. The backend's duplicate check (`routes_auth.py:24-25`) is a read-then-write with no unique-constraint handling, so concurrent registrations race; the DB's `unique=True` on `users.email` (`user.py:10`) will then raise an **unhandled `IntegrityError` → 500**.

**Fix:** consume `loading` — disable the divs and show "…". Ideally also make them real `<button>`s (they are keyboard-inaccessible as divs).

### 4.4 `Content-Disposition` is invisible to the browser — **MEDIUM**

`exportApi.js:36` reads `res.headers.get('Content-Disposition')` to recover the server's filename. `routes_export.py:76` sets it correctly. But `main.py:22-28` configures `CORSMiddleware` **without `expose_headers`**, and `Content-Disposition` is not a CORS-safelisted response header. Cross-origin (which is always — frontend on Vercel, backend on Render), `.get()` returns `null` and the code silently falls back to `export-${versionId}.${format}` (`:35`).

The backend filename happens to be the same string today (`routes_export.py:71`), so nothing looks broken — but the header-reading code at `:36-40` is **entirely dead in production**, and the moment anyone improves the server-side filename it will silently not take effect.

**Fix:** add `expose_headers=["Content-Disposition"]` to the middleware. Note the backend tests **cannot** catch this — `test_export.py:33` asserts on `res.headers["content-disposition"]` via `TestClient`, which does not enforce CORS.

### 4.5 No token persistence — refresh logs the user out — **MEDIUM**

`grep -rn "localStorage\|sessionStorage\|Cookie" frontend/src` → **zero hits**. The JWT lives only in `App.jsx:8`'s `useState`. On any hard refresh, `user` resets to `undefined`, `App.jsx:19` sees `user === undefined`, and redirects `/dashboard` → `/`. Every refresh is a logout, mid-work.

Compounding it, `App.jsx` uses **two different sentinels**: `undefined` = logged out, `null` = guest (`Login.jsx:72` calls `onAuth(null)`). The guards test `user !== undefined` (`:15`, `:19`), so `null` counts as authenticated. Anyone who later writes the idiomatic `setUser(null)` to mean "log out" will instead put the app into guest mode. Use a single explicit shape (`{status: 'anon'|'guest'|'user', ...}`) or at minimum a separate `isGuest` flag.

Also: `onLogout` is only rendered inside `{user && …}` (`dashboard.jsx:62-67`), so a **guest has no way to leave guest mode** without editing the URL.

### 4.6 `validate-key` reports network failures as "Invalid API key" — **MEDIUM**

`llm_service.py:18-30`:

```python
async def test_provider_key(provider, api_key) -> bool:
    try:
        ...
    except Exception:
        return False        # ← every failure collapses to False
```

`test_openai_key` (`:32-38`) catches only `openai.AuthenticationError`; anything else — DNS failure, timeout, 429, 500 — escapes to the outer `except Exception` and becomes `False`. `routes_validate_key.py:38-39` then raises **401 "Invalid API key."**

So a transient network blip tells the user their key is invalid. Distinguish auth failures (401) from upstream failures (502/503), mirroring the `ProviderAuthError` / `ProviderError` split that `providers/` already models correctly.

### 4.7 `TemplateResponse.model_config` is at module scope — **MEDIUM**

`routes_templates.py:12-18`:

```python
class TemplateResponse(BaseModel):
    id: int
    name: str
    category: str
    content: str

model_config = {"from_attributes": True}      # ← dedented; module-level global
```

Verified at runtime:

```
class from_attributes:   None
module-level stray var:  {'from_attributes': True}
TemplateResponse.model_validate(<Template ORM obj>) → ValidationError
```

Compare `version_schema.py:23`, where the identical line **is** correctly indented inside the class.

The endpoint still returns 200 (all 6 `test_templates.py` tests pass) because FastAPI's internal `ModelField.validate` passes `from_attributes=True` explicitly when serializing a `response_model`. So this is **latent, not currently breaking** — but the model is misconfigured, `model_validate` on an ORM object fails, and it depends on a FastAPI implementation detail. Indent the line by 4 spaces.

### 4.8 React hook dependency problems — **MEDIUM**

ESLint reports 4 `react-hooks/exhaustive-deps` warnings and 1 `react-hooks/set-state-in-effect` **error**:

| Location | Issue |
|---|---|
| `DiffVerisonPicker.jsx:20` | **error** `set-state-in-effect` — `loadVersions()` called synchronously in the effect body triggers cascading renders |
| `DiffVerisonPicker.jsx:21` | missing dep `loadVersions` |
| `TemplateLibrary.jsx:27` | missing dep `loadTemplates` |
| `VersionSelector.jsx:39` | missing dep `loadVersions` |
| `ModelSelector.jsx:33` | `safeSelectedModels` is a fresh array each render, so the `useMemo` at `:45-52` recomputes every render — the memo does nothing |

None currently misbehave (the functions are stable per render in practice), but they are exactly the class of latent bug that bites during a refactor. Wrap the loaders in `useCallback` and `safeSelectedModels` in `useMemo`.

**Related, and real today:** none of the three data-loading effects has a **cleanup or abort**. `VersionSelector.jsx:32-39` debounces search by 300 ms and fires a request per settled keystroke with no `AbortController`. Responses can land out of order, so a slow early request can overwrite a fast later one — the classic stale-search-results race. `grep -rn "AbortController\|isMounted\|signal"` → zero hits.

### 4.9 State update after unmount — **LOW**

`ExportDropdown.jsx:21-23` schedules `setMessage` 3 seconds out with no `clearTimeout` on unmount. `ExportDropdown` is conditionally rendered (`dashboard.jsx:101-103`), so logging out within 3 s of an export fires a setState on an unmounted component. Harmless in React 19 (no warning), still a leak. Store the timer id and clear it in a `useEffect` cleanup.

### 4.10 `DiffView` guard is unreachable and its message is wrong — **LOW**

`DiffView.jsx:43-49` renders `"You need at least one saved version to compare."` when `totalVersions < 1`. Two problems:

1. **Wrong threshold.** Comparison needs **two** versions; the check and the copy both say one.
2. **Unreachable.** The only producer is `DiffVerisonPicker.handleCompare` (`:31-35`), which passes `versions.length`, and the Compare button is `disabled` unless exactly 2 are selected (`:67`) — so `totalVersions >= 2` always. Additionally `dashboard.jsx:129` renders `DiffView` only when both `versionA && versionB`.

`test/DiffView.test.jsx:46-49` passes `totalVersions={0}` directly, testing a state the app cannot produce — a green test guarding dead code. Either make it `< 2` with matching copy, or delete the branch and its test.

### 4.11 `VersionSelector` can hang on "Loading versions…" forever — **LOW**

`VersionSelector.jsx:18-30`:

```js
async function loadVersions(search = '') {
  if (!token) return          // ← returns before the try/finally
  try { setLoading(true); ... } finally { setLoading(false) }
}
```

`loading` initializes to `true` (`:7`). If `token` is falsy, the guard returns **before** the `finally`, so `loading` stays `true` permanently and the component is stuck on `"Loading versions..."` (`:129`).

Not reachable today — `dashboard.jsx:106` only renders it when `user` is truthy, and `Login.jsx:61` always supplies a token. But it becomes reachable the moment the login response shape changes or guest mode gains a version list. Move the guard inside, or `setLoading(false)` before returning.

### 4.12 `computeDiff` is uncapped O(n·m) — **MEDIUM**

`DiffView.jsx:3-39` builds a full `(oldWords+1) × (newWords+1)` LCS DP table on the **main thread, during render** (`:51`), with no size cap. Two 2,000-word prompts allocate 4 million array cells; two 5,000-word prompts allocate 25 million and will lock the tab for seconds. Prompt text is `Text` in the DB (`prompt_version.py:15`) with **no length limit** (`version_schema.py:7` sets only `min_length=1`).

Cap the word count (diff the first N words, note the truncation), or swap in a linear-space Myers diff.

### 4.13 Backend 500 risks — **MEDIUM**

- **`routes_auth.py:24-26`** — `get_user_by_email` then `create_user` is a check-then-act race. `users.email` is `unique=True` (`user.py:10`), so two concurrent registrations produce an unhandled `IntegrityError` → 500. Made reachable by §4.3's double-submit. Catch `IntegrityError` and return 409.
- **`main.py:11-18`** — `ensure_prompt_versions_tag_column()` runs at **import time** and calls `inspector.get_columns("prompt_versions")` unguarded. If the table does not exist (fresh non-SQLite DB, or a partial `create_all`), this raises during module import and the app **fails to boot**. It works today only because `create_all` on `:9` runs first.
- **`main.py:4-9`** — `Base.metadata.create_all` is called after importing only `user` and `prompt_version`. The `templates` table gets created solely because `:7`'s `from app.api.router import api_router` transitively imports `routes_templates` → `models.template`. Reorder those imports and the templates table silently stops being created. Import `app.models.template` explicitly.
- **`llm_service.py:14-16`** — `import openai`, `import anthropic`, `from google import genai` are **unguarded**, unlike all three `providers/*` modules which wrap their SDK imports in `try/except`. Since `router.py:4` → `routes_validate_key.py:3` → `llm_service`, a single missing SDK takes down the **entire application** at import. Adopt the guarded pattern.

### 4.14 Minor

- `exportApi.js:28` — `catch (e)` with unused binding (ESLint `no-unused-vars`). Use bare `catch {`, as `versionsApi.js:130` already does.
- `exportApi.js:54` — `revokeObjectURL` is called immediately after `a.click()`; some browsers need the URL alive until the download starts. Defer to a `setTimeout(…, 0)`.
- `ResponseDisplay.jsx:44` — `key={r.model}` breaks if the same model appears twice in a batch. `routes_execute.py:84` iterates `request.models` without dedupe, so `["gpt-4o","gpt-4o"]` yields duplicate keys.
- `routes_validate_key.py:31` — message says `"Unsupported model"` but the check is on `request.provider`. Should read "Unsupported provider". `test_validate_key.py:47` asserts the wrong string, cementing it.
- `datetime.utcnow()` is deprecated in Python 3.12+ — `user.py:12`, `prompt_version.py:21`, `auth_service.py:23`. Produced **67 warnings** in the pytest run. Use `datetime.now(datetime.UTC)`.
- `llm_service.py:70,73` — `print()` used for error reporting in a server process. Use `logging`.
- `README.md:155` — "The frontend is pre-configured to communicate with the backend at `http://localhost:8000`" is **false**; it is hardcoded to the Render URL (§2.1). `README.md:3` also lists only "OpenAI and Google Gemini" while Anthropic is fully wired and listed at `:58`.

---

## 5. Tests

### Results — actually executed

**Backend — 59 passed, 0 failed** (12.36s, 67 warnings).

> ⚠️ **I did not run this the way the task suggested.** `backend/tests/conftest.py:8-21` is an `autouse` fixture that runs `db.query(PromptVersion).delete()` and `db.query(UserInfo).delete()` against `SessionLocal` — which resolves to `settings.DATABASE_URL`, defaulting to `sqlite:///./promptbox.db` (`config.py:7`). **There is no test-database override.** A plain `pytest` in `backend/` would have wiped the checked-in dev database.
>
> I ran it with `DATABASE_URL` pointed at a scratch file instead, and verified `backend/promptbox.db` was untouched (md5 `3349d101c77bb145b87a19263b13208b` before and after). A backup was also taken.

**Frontend — 52 passed, 4 failed** (18 files, 56 tests, 2.51s).

> `npx vitest run --reporter=basic` **fails to start** — Vitest 4 removed the `basic` reporter (`Failed to load custom Reporter from basic`). Use `--reporter=dot` or `--reporter=default`.

All 4 failures share one root cause — §2.1's `API_BASE` drift:

| Test | Expected | Actual |
|---|---|---|
| `api.client.test.js:12` | `http://localhost:8000/health` | `https://promptbox-9d83.onrender.com/health` |
| `executeApi.test.js:29` | `http://localhost:8000/api/execute` | `https://promptbox-9d83.onrender.com/api/execute` |
| `vesrionsApi.test.js:20` | `http://localhost:8000/api/versions/` | `https://promptbox-9d83.onrender.com/api/versions/` |
| `vesrionsApi.test.js:32` | `http://localhost:8000/api/versions/?search=foo` | `https://promptbox-9d83.onrender.com/api/versions/?search=foo` |

Fixing §2.1 fixes all four. **HIGH.**

### Critical: tests share state with development — **HIGH**

Beyond the wipe risk, `test_templates.py:7-17` seeds two `Template` rows and **never cleans them up** (`conftest.py` deletes only users and versions). Every `pytest` run permanently injects `"Basic Q&A"` (category `structural`) and `"Code Review"` (category `use_case`) into whatever database it points at. Those are the **old** category names from before the rename (§2.4) — so running the tests pollutes the dev DB with templates the UI cannot style.

**Fix:** in `conftest.py`, override `get_db` with a `tmp_path`-scoped SQLite session via `app.dependency_overrides`, so tests are hermetic by construction.

### Coverage gaps

| Untested | Rating |
|---|---|
| **`AnthropicProvider` entirely.** `test_execute.py` covers OpenAI (`:31`) and Gemini (`:45`) only. This is precisely why §4.1's 401/502 bug survived. | **HIGH** |
| **`PATCH`/`DELETE` version flows in `VersionSelector.jsx`** — `saveEdit` (`:55-83`) and `handleDelete` (`:85-102`) have backend tests but no frontend test drives the edit/delete UI. | MEDIUM |
| **`routes_export.py` `serialize_txt`/`serialize_md` as units** — only exercised through HTTP. | LOW |
| **`llm_service.py` — zero direct tests.** `test_validate_key.py` mocks `test_provider_key` out entirely (`:12`, `:24`), so the duplicate-function bug (§1.5) and the error-collapsing bug (§4.6) are both invisible to the suite. | **HIGH** |
| **`getTemplate` / `getVersion` / `getHealth`** — `getHealth` has a (failing) test; the other two have none, consistent with having no callers (§1.3). | LOW |
| **CORS configuration** — untestable via `TestClient`; §4.4 needs a real browser or an explicit `Origin`-header test. | MEDIUM |

### Tests that assert little

| Test | Problem |
|---|---|
| `test/App.test.jsx:4-6` | `render(<App />)` with **no assertion at all**. Passes if the component renders literally anything. Also imports `screen` unused. |
| `test/DiffView.test.jsx:46-49` | Asserts on `totalVersions={0}`, a state the app cannot produce (§4.10). Green test guarding dead code. |
| `test/register.test.jsx:75-89` | Named `"blocks submission when email is invalid"` but sets email to `""` — it tests the **empty** case, duplicating `:56` in `login.test.jsx` and `:18` in `components/Login.test.jsx`. Email-*format* validation has **zero** coverage, and `Login.jsx:35` only checks `.trim()`, so `notanemail` reaches the server. |
| `test_validate_key.py` (all 4) | `test_provider_key` is fully mocked, so these test only `routes_validate_key`'s branching — not one line of real validation logic. Reasonable in isolation, but nothing else covers `llm_service` either. |
| `test_security.py:3-5` | `assert hashed != "secret"` — true of any transformation, including `"secret" + "x"`. Assert the bcrypt prefix (`$2b$`) instead. |

### Duplicated test coverage

Three files test `Login.jsx`, with overlapping cases:

```
components/Login.test.jsx:18  "prevents submission when email is empty"
test/login.test.jsx:56        "blocks submission when email field is empty"
test/register.test.jsx:75     "blocks submission when email is invalid"   ← also tests empty

components/Login.test.jsx:31  "prevents submission when password is under 8 characters"
test/login.test.jsx:37        "blocks submission when password is under 8 characters"
test/register.test.jsx:58     "blocks submission when password is under 8 characters"
```

Six tests covering two behaviors. Consolidate into one `test/Login.test.jsx` and delete `components/Login.test.jsx` (which is also the only test outside `src/test/`). **MEDIUM.**

---

## 6. Lint

`cd frontend && npx eslint src --max-warnings=0` → **118 problems (114 errors, 4 warnings)**.

### By rule

| Rule | Severity | Count |
|---|---|---|
| `no-undef` | error | **107** |
| `no-unused-vars` | error | 6 |
| `react-hooks/exhaustive-deps` | warn | 4 |
| `react-hooks/set-state-in-effect` | error | 1 |

### The 107 `no-undef` errors are one config bug

`eslint.config.js:18` sets `globals: globals.browser` only. But `vite.config.js:9` sets `globals: true`, so tests use `describe`/`test`/`it`/`expect`/`vi` without importing them — and ESLint has never been told those exist. Every occurrence in a file that relies on auto-globals is flagged. `global` (Node) is flagged for the same reason.

**Fix — one config block clears ~107 of 118 errors:**

```js
{
  files: ['**/*.test.{js,jsx}', 'src/test/**'],
  languageOptions: { globals: { ...globals.node, ...globals.vitest } },
}
```

(or `import vitestGlobals from 'eslint-plugin-vitest/globals'`). **HIGH.**

Note `package.json:9` runs `eslint .` while the task specified `eslint src`; `dist` is ignored (`eslint.config.js:8`) but `frontend/docs/` is **not**, so `npm run lint` will also try to lint the generated JSDoc `scripts/prettify/*.js`. Add `'docs'` to `globalIgnores`.

### The 6 `no-unused-vars` errors

| Location | Symbol | Verdict |
|---|---|---|
| `src/components/Login.jsx:15` | `loading` | **Real bug** — §4.3 |
| `src/api/exportApi.js:28` | `e` | Use bare `catch {` |
| `src/test/App.test.jsx:1` | `screen` | Delete |
| `src/test/ModelSelector.test.jsx:4` | `expectTypeOf` | Delete |
| `src/test/PromptEditor.test.jsx:1` | `test` | Delete |
| `src/test/VersionSelector.test.jsx:5` | `version` (from `'react'`!) | Delete — a stray autocomplete import |

### By file (top offenders)

```
19  src/test/TemplateLibrary.test.jsx      4  src/test/ModelSelector.test.jsx
15  src/test/ExportDropdown.test.jsx       3  src/test/api.client.test.js
14  src/test/DiffView.test.jsx             2  src/components/DiffVerisonPicker.jsx
13  src/test/login.test.jsx                2  src/test/App.test.jsx
12  src/test/VersionSelector.test.jsx      1  each: exportApi.js, Login.jsx,
12  src/test/register.test.jsx                ModelSelector.jsx, TemplateLibrary.jsx,
 9  src/test/MultiModelPrompt.test.jsx        VersionSelector.jsx, PromptEditor.test.jsx,
 5  src/components/Login.test.jsx             executeApi.test.js, vesrionsApi.test.js
```

**Only 5 of 118 problems are in non-test source.** After the globals fix, the suite is essentially clean — which makes `--max-warnings=0` a realistic CI gate. **HIGH.** No `--fix` was run.

---

## 7. Safe to delete

### Tier 1 — definitely dead, delete without further checking

| Path | Why |
|---|---|
| `frontend/src/components/Navbar.jsx` | 0 bytes; zero references anywhere |
| `backend/app/schemas/user_schema.py` | 0 bytes; zero references anywhere |
| `frontend/src/assets/react.svg` | Zero references (Vite scaffold leftover) |
| `backend/app/services/llm_service.py:40-50` | `test_anthropic_key` shadowed by the redefinition at `:60-74` |
| `backend/app/services/llm_service.py:55` | `response =` assigned, never read |
| `frontend/src/test/App.test.jsx:1` | unused `screen` import |
| `frontend/src/test/ModelSelector.test.jsx:4` | unused `expectTypeOf` import |
| `frontend/src/test/PromptEditor.test.jsx:1` | unused `test` import |
| `frontend/src/test/VersionSelector.test.jsx:5` | unused `import { version } from 'react'` |
| `frontend/src/components/TemplateLibrary.css:65-73` | `.structural` / `.use_case` — categories no longer exist |
| `frontend/src/App.css:279-289` | `.validation-success` / `.validation-error` — zero JSX references |

### Tier 2 — looks unused, verify first

| Path | Verify what |
|---|---|
| `backend/app/providers/llm_provider_base.py` | Nothing imports `LLMProvider`. **Better move:** repurpose it as the shared base in §2.3 rather than delete. |
| `frontend/src/api/templatesApi.js:24-37` (`getTemplate`) | Zero callers, but backs a live tested endpoint. Delete client + endpoint together, or wire up a template preview. |
| `frontend/src/api/versionsApi.js:63-81` (`getVersion`) | Same. |
| `frontend/src/api/client.js:4-11` (`getHealth`) | Only a failing test uses it. Consider **keeping** and wiring a cold-start indicator (§1.3). |
| `backend/app/api/routes_auth.py:11,14-18` (`EMAIL_RE`, `_validate`) | Unreachable behind Pydantic; confirm no `EmailStr`-accepted address fails `EMAIL_RE`, then delete along with the two call sites at `:23` and `:32`. |
| `frontend/src/components/DiffView.jsx:43-49` | Unreachable guard. Prefer **fixing** to `< 2` with corrected copy over deleting. |
| `frontend/src/components/ModelSelector.jsx:82-110` + legacy props `:23-28` | Dead in-app (`dashboard.jsx:71-77` never passes `provider`/`setProvider`), but `test/ModelSelector.test.jsx` may exercise them. Update tests first, then delete. |
| `frontend/src/components/PromptEditor.jsx:28-30` (`executePrompt` branch) | Unreachable in-app (`dashboard.jsx:80` always passes `models`), but `test/PromptEditor.test.jsx:16` spies on it. Update tests first. |
| `frontend/docs/` (32 files) | Stale (§1.7) and unregeneratable. Either add the jsdoc toolchain, or delete + gitignore + drop `README.md:192`. |
| `frontend/src/components/Login.test.jsx` | Fully duplicated by `test/login.test.jsx` + `test/register.test.jsx`; merge before deleting. |

### Explicitly NOT dead — do not delete

- `frontend/src/assets/person.png`, `email.png`, `password.png` — used at `Login.jsx:4-6`
- `frontend/public/vite.svg` — favicon, `index.html:5`
- `backend/app/providers/anthropic_provider.py` — wired at `routes_execute.py:12,31-32`
- `backend/docs/openapi.json` — verified byte-current
- `frontend/src/components/ErrorMessage.jsx` — unused, but **adopt it** (§1.4) rather than delete
- `frontend/src/api/executeApi.js` `executePrompt` — reachable via `PromptEditor.jsx:29`

---

## 8. Suggested order of work

1. **§2.1** — one `API_BASE` from `import.meta.env`. Fixes 4 failing tests, unblocks docs regeneration, corrects the README. *(1 file, ~6 edits)*
2. **§6** — add vitest globals to `eslint.config.js`. Clears ~107 of 118 lint errors. *(1 file, 4 lines)*
3. **§4.1** — `ProviderAuthError` → `ProviderError` at `anthropic_provider.py:42`, plus the missing Anthropic test. *(1 word + 1 test)*
4. **§4.2** — `try/catch/finally` in `ModelSelector.handleValidate`. *(3 lines)*
5. **§5** — `app.dependency_overrides[get_db]` in `conftest.py` so tests stop touching the dev DB. *(1 fixture)*
6. **§4.3** — consume `loading` in `Login.jsx`; catch `IntegrityError` in `routes_auth`.
7. **§2.2 + §3.3** — shared `request()` helper carrying `extractError`. Removes ~60 duplicated lines and fixes `[object Object]` errors in one place.
8. Tier-1 deletions (§7), then the remaining MEDIUM items.

Steps 1–5 are roughly an hour and take the repo from *4 failing tests + 118 lint errors + a destructive test suite* to *green, lintable, and safe to run*.
