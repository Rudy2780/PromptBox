# PromptBox — Security & Configuration Audit

**Scope:** full repository at `/Users/rrutiaga/Desktop/PromptBox` (branch `main`, commit `2dc37bb`), plus a review of the unmerged remote branch `origin/cleanup/codebase` (`f26fa18`) where it changes security-relevant code.
**Method:** source read of every backend module and every frontend module under `src/`, plus `git ls-files`, full `git log --all` history scan, `.gitignore` verification, and inspection of the on-disk SQLite file.
**Date:** 2026-08-24
**Nature:** defensive review of the owner's own project. Report only — no files were modified.

---

## Summary table

| # | Severity | Finding | Location |
|---|---|---|---|
| C1 | **CRITICAL** | JWT signing secret falls back to a hardcoded default that is published in the README → forgeable tokens, full account takeover | `backend/app/config.py:8` |
| H1 | **HIGH** | LLM-calling endpoints (`/api/execute`, `/api/prompt`, `/api/validate-key`) have no authentication and no rate limiting → open LLM relay, stolen-key validation oracle, unbounded batch loop | `backend/app/api/routes_execute.py:46,71`, `routes_validate_key.py:28` |
| H2 | **HIGH** | Autouse pytest fixture mass-deletes all users and all prompt versions from whatever database `DATABASE_URL` points at | `backend/tests/conftest.py:8-21` |
| M1 | MEDIUM | Raw upstream provider exception text is returned to unauthenticated callers and printed to stdout | `llm_service.py:70,73`, `openai_provider.py:54`, `gemini_provider.py:47`, `anthropic_provider.py:42` |
| M2 | MEDIUM | Passwords of 73–128 characters raise an unhandled `ValueError` in bcrypt 5.0.0 → HTTP 500 on register **and** login | `schemas/auth.py:5` + `utils/security.py:5,8` |
| M3 | MEDIUM | No rate limiting or lockout on `/auth/login`; `/auth/register` returns 409 → account enumeration | `routes_auth.py:21-39` |
| M4 | MEDIUM | Default database is SQLite on Render's ephemeral disk → silent total data loss on redeploy; no safe concurrency | `backend/app/config.py:7` |
| M5 | MEDIUM | Production backend URL hardcoded in 6 frontend files → running the frontend locally sends real provider API keys to the production host | `frontend/src/api/*.js:1`, `Login.jsx:8` |
| M6 | MEDIUM | JWTs are 24h, non-revocable, no `jti`/`iat`/`aud`/`iss`; logout is client-state only | `auth_service.py:20-25`, `App.jsx:19` |
| L1 | LOW | `/docs`, `/redoc`, `/openapi.json` exposed in production | `backend/app/main.py:20` |
| L2 | LOW | `/api/templates/*` unauthenticated | `routes_templates.py:20,30` |
| L3 | LOW | `int(user_id)` on token subject can raise unhandled `ValueError` → 500 | `dependencies/auth.py:32` |
| L4 | LOW | `%` / `_` in the `search` query parameter are not escaped before `LIKE` | `routes_versions.py:44` |
| L5 | LOW | `allow_credentials=True` is unnecessary (Bearer-only app); CORS provides no protection for the unauthenticated endpoints | `backend/app/main.py:22-28` |
| L6 | LOW | Anthropic provider maps *all* failures to `ProviderAuthError` → every Anthropic outage reports as HTTP 401 "invalid key" | `anthropic_provider.py:42` |
| L7 | LOW | `model_config` declared outside the Pydantic class | `routes_templates.py:18` |
| — | **CLEAN** | Object ownership / IDOR, SQL injection, frontend XSS, secrets in git history, provider keys in the frontend bundle, password hashing, code execution of model output | see §"Areas that are clean" |

---

## Claims vs. reality

The brief described the project as "React+Vite frontend / FastAPI+PostgreSQL backend, deployed on Vercel and Render, with GitHub/Google OAuth." What the code actually contains:

| Claim | Reality |
|---|---|
| React + Vite frontend | **True.** React 19 + Vite 7, `frontend/package.json:14-32`. |
| FastAPI backend | **True.** `fastapi==0.135.1`, `backend/app/main.py:20`. |
| PostgreSQL | **False.** SQLite is the only configured database: `DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./promptbox.db"` (`config.py:7`). No `psycopg`/`asyncpg` in `requirements.txt`. README line 50 also says SQLite. See M4. |
| Deployed on Vercel + Render | **Partly true, but nothing in-repo configures it.** There is no `vercel.json`, `render.yaml`, `Procfile`, `Dockerfile`, or CI config tracked in git. The deployment is inferred only from two hardcoded URLs: `https://promptbox-9d83.onrender.com` (frontend API base) and `https://prompt-box-seven.vercel.app` (CORS allowlist, `main.py:24`). Deployment is therefore entirely dashboard-configured and unversioned — including whether `JWT_SECRET` is set (see C1). |
| GitHub/Google OAuth | **False. There is no OAuth anywhere.** A repo-wide grep for `oauth`, `authlib`, `client_secret`, `accounts.google`, `github.com/login` returns zero hits in `backend/app` and `frontend/src`. Authentication is email + password only (`routes_auth.py`), plus a "Continue as Guest" button (`Login.jsx:71-74`). |
| `backend/promptbox.db` looks committed | **False — and this is good news.** `git ls-files \| grep -iE '\.db\|\.env\|sqlite'` returns nothing. `git check-ignore -v` confirms `backend/.gitignore:1:*.db` matches it. The file exists on disk only, and it is **empty**: 0 rows in `users`, 0 rows in `prompt_versions`, and no key-shaped strings anywhere in the file. |

---

# Findings

## C1 — CRITICAL: JWT signing secret falls back to a hardcoded, publicly documented default

**Evidence**

`backend/app/config.py:8`
```python
JWT_SECRET = os.getenv("JWT_SECRET") or "dev-secret-change-me"
```

`README.md:100`
```
| `JWT_SECRET` | Secret key used to sign JWT tokens | `dev-secret-change-me` |
```

Consumers: `backend/app/services/auth_service.py:25` (`jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")`) and `backend/app/dependencies/auth.py:19` (`jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])`).

**Why it matters concretely.** HS256 is symmetric: the signing key *is* the verification key. If `JWT_SECRET` is not set in the Render environment — and nothing in the repository sets or enforces it, because there is no `render.yaml` or any other tracked deploy config — the production API signs and verifies tokens with a string that is written down in the public README. An attacker needs no account, no interaction, and no leaked data: they encode `{"sub": "1", "exp": <future>}` with HS256 and `dev-secret-change-me`, send it as `Authorization: Bearer …`, and `get_current_user` returns user 1. From there every authenticated route is theirs — read, rename, and delete any user's saved prompts (`routes_versions.py:35,53,65,86`) and export any user's prompt text (`routes_export.py:34`). Because the token subject is a small sequential integer (`models/user.py:9`), enumerating every account is a loop from 1 upward.

The `or` (rather than a proper default) makes this worse in a second way: an environment variable that is present but **empty** (`JWT_SECRET=`) is falsy in Python and silently falls through to the same default. A deploy where someone "set the secret" but pasted an empty value is indistinguishable at runtime from one where they never set it.

**Remediation.** Remove the fallback entirely and fail closed at import time:
```python
JWT_SECRET = os.environ["JWT_SECRET"]          # KeyError at startup if unset
if len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must be at least 32 bytes")
```
Then: generate a fresh secret (`python -c "import secrets; print(secrets.token_urlsafe(48))"`), set it in the Render dashboard, and **rotate it now** — assume every currently-outstanding token is forged until proven otherwise; rotation invalidates all of them. Delete the default value from `README.md:100` (document that the variable is required, not what its value is). Add the same startup check to a `/health` readiness probe if you want it visible.

---

## H1 — HIGH: the LLM-calling endpoints are unauthenticated and unmetered

**Evidence**

`backend/app/api/router.py:14,16` mounts these with no dependency:
```python
api_router.include_router(validate_key_router, prefix="/api")
api_router.include_router(execute_router)
```

`backend/app/api/routes_execute.py:46-47`
```python
@router.post("/api/execute", response_model=ExecuteResponse)
def execute(request: ExecuteRequest) -> ExecuteResponse:
```
`backend/app/api/routes_execute.py:71-72`
```python
@router.post("/api/prompt", response_model=PromptBatchResponse)
def prompt_batch(request: PromptBatchRequest) -> PromptBatchResponse:
```
`backend/app/api/routes_validate_key.py:28-29`
```python
@router.post("/validate-key")
async def validate_key(request: ValidateKeyRequest):
```

None of the three declares `user: UserInfo = Depends(get_current_user)`. Compare with `routes_versions.py:17` and `routes_export.py:38`, which do.

**Complete list of unauthenticated routes:**

| Route | Auth | Assessment |
|---|---|---|
| `GET /` (`main.py:32`) | none | fine — static status string |
| `GET /health/` (`routes_health.py:5`) | none | fine |
| `POST /auth/register` (`routes_auth.py:21`) | none | by design; see M3 |
| `POST /auth/login` (`routes_auth.py:30`) | none | by design; see M3 |
| **`POST /api/validate-key`** (`routes_validate_key.py:28`) | **none** | **this finding** |
| **`POST /api/execute`** (`routes_execute.py:46`) | **none** | **this finding** |
| **`POST /api/prompt`** (`routes_execute.py:71`) | **none** | **this finding** |
| `GET /api/templates/` (`routes_templates.py:20`) | none | L2 |
| `GET /api/templates/{id}` (`routes_templates.py:30`) | none | L2 |
| all `/api/versions/*`, `/api/export/*` | **`get_current_user`** | correctly protected |

**Why it matters concretely.** The backend URL is a public constant in the shipped JavaScript bundle (`frontend/src/api/executeApi.js:1`), so anyone who opens devtools on the Vercel site knows the endpoint. Three concrete abuses follow:

1. **Stolen-key validation oracle.** `POST /api/validate-key` takes `{provider, api_key}` and answers 200 (valid) or 401 (invalid) against OpenAI, Anthropic, and Gemini. That is exactly the primitive someone with a dump of scraped keys wants, and your server does it for them anonymously, from your IP, with no throttle. `routes_validate_key.py:36-39`.
2. **Open LLM relay.** `POST /api/execute` and `POST /api/prompt` accept an arbitrary prompt plus the caller's own key and forward it upstream. Your Render instance becomes a free anonymizing proxy for third-party LLM traffic — the provider sees your server's IP, not the abuser's. That is a reputation and abuse-report liability even though the abuser pays for the tokens.
3. **Compute exhaustion.** `routes_execute.py:74-102` loops over `request.models` with **no cap on list length**, calling a blocking network request per element (`PromptBatchRequest.models: List[str]`, `schemas/execute_schema.py:19`, has no `max_length`). `prompt` likewise has no `max_length` (`execute_schema.py:6,18`). A single request with 500 model entries and a megabyte prompt occupies a request thread for minutes. On a small Render dyno a handful of these is a denial of service, and nothing anywhere in the repo rate-limits it — there is no `slowapi`, no `limits`, no reverse-proxy config, no per-IP counter.

Note that CORS does **not** mitigate any of this. `main.py:24`'s origin allowlist is enforced by browsers only; `curl` ignores it entirely.

**Remediation.**
- Put `Depends(get_current_user)` on `/api/execute`, `/api/prompt`, and `/api/validate-key`. The frontend already holds a token in `user.token` (`dashboard.jsx:102,108`) and passes it on other calls, so this is a small frontend change (add the `Authorization` header in `executeApi.js` and `client.js`) — and the dashboard already renders these components only when a user exists.
- Add per-user and per-IP rate limits on the three endpoints, e.g. `slowapi` with a Redis or in-process bucket: something like 30 executions/hour/user and 10 key validations/hour/IP.
- Bound the inputs: `prompt: str = Field(max_length=32_000)`, `models: List[str] = Field(max_length=4)`, and de-duplicate `models` before the loop.
- Consider whether "Continue as Guest" (`Login.jsx:71-74`) needs to keep working; if it does, give guests a short-lived signed token rather than leaving the endpoints open.

---

## H2 — HIGH: the test suite deletes every user and every saved prompt from the configured database

**Evidence**

`backend/tests/conftest.py:1-21`
```python
from app.main import app
from app.database import SessionLocal
...
@pytest.fixture(autouse=True)
def clear_users():
    db = SessionLocal()
    db.query(PromptVersion).delete(synchronize_session=False)
    db.query(UserInfo).delete(synchronize_session=False)
    db.commit()
```

`SessionLocal` is bound to `ENGINE`, which is built from `settings.DATABASE_URL` (`database.py:5-7`, `config.py:7`) — the *real* configured database, whatever it is. There is no test-database override, no in-memory SQLite fixture, no `dependency_overrides[get_db]`. The fixture is `autouse=True`, so it runs before **and** after every single test in the suite.

Compounding it, importing `app.main` (line 3) executes module-level side effects against that same database: `Base.metadata.create_all(bind=ENGINE)` (`main.py:9`) and `ensure_prompt_versions_tag_column()` (`main.py:18`), which issues a live `ALTER TABLE prompt_versions ADD COLUMN tag VARCHAR(32)` (`main.py:16`).

**Why it matters concretely.** `README.md:87-95` instructs the developer to create `backend/.env` containing `DATABASE_URL`, and `python-dotenv` loads it automatically (`config.py:2-4`). The moment anyone points that variable at a shared or production database — which is the natural thing to do when debugging a production issue, and the exact migration the owner is contemplating with the move to Postgres — running `pytest tests` (the command in `README.md:166`) silently and irrecoverably deletes every registered account and every saved prompt version. There is no confirmation, no dry run, and the destruction happens in a fixture that runs before the first test even starts. CI running the suite with a production `DATABASE_URL` in its environment would do the same.

**Remediation.** Make the test database explicit and impossible to confuse with a real one:
```python
# conftest.py
TEST_DB = "sqlite:///./test_promptbox.db"     # or sqlite:///:memory:
engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine)
app.dependency_overrides[get_db] = lambda: ...   # yield a TestingSessionLocal
```
and add a hard guard that refuses to run destructive fixtures against anything else:
```python
assert "test" in str(engine.url), f"refusing to run tests against {engine.url}"
```
Separately, move `create_all` and `ensure_prompt_versions_tag_column` out of `main.py` module scope into an explicit startup/migration command so that merely importing the app cannot alter a schema. Long term, use Alembic rather than an inline `ALTER TABLE`.

---

## M1 — MEDIUM: raw upstream provider exception text reaches unauthenticated clients and stdout

**Evidence**

Printed to stdout (Render logs):
`backend/app/services/llm_service.py:69-73`
```python
    except anthropic.AuthenticationError as e:
        print(f"Anthropic auth error: {e}")
        return False
    except Exception as e:
        print(f"Anthropic other error: {type(e).__name__}: {e}")
```

Returned to the HTTP client:
- `backend/app/providers/openai_provider.py:54` — `raise ProviderError(f"OpenAI provider error: {exc}")`
- `backend/app/providers/gemini_provider.py:47` — `raise ProviderError(f"Gemini provider error: {exc}")`
- `backend/app/providers/anthropic_provider.py:42` — `raise ProviderAuthError(f"Anthropic provider error: {exc}")`
- `backend/app/api/routes_execute.py:63,66,96,98` — `raise HTTPException(status_code=…, detail=str(exc))`
- surfaced verbatim in the browser via `executeApi.js:29-30` → `dashboard.jsx:125`

**Why it matters concretely.** The full text of any SDK exception — request URLs, upstream request IDs, organization identifiers, internal error payloads, occasionally header fragments — is concatenated into an HTTP `detail` and handed to a caller who did not have to authenticate (see H1). Whether an *API key* itself can appear there depends on the SDK: the providers here all pass the key in a header (`openai.OpenAI(api_key=…)`, `anthropic.Anthropic(api_key=…)`, `genai.Client(api_key=…)`), so the common failure paths do not stringify it — but `requirements.txt:23` also pins the legacy `google-generativeai==0.8.6`, whose transport places the key in a `?key=` query parameter, and any future switch to that client (or to a raw `httpx`/`requests` call) turns these lines into a direct key-disclosure path with no other code change. The `print()` calls are a definite leak of upstream error content into Render's log stream regardless.

I did check the rest of the exception surface and it is clean: `providers/exceptions.py` defines two bare exception classes with no message handling, `main.py` installs no custom exception handler and no `traceback` import exists anywhere in the backend, and there is no `logging` configuration at all.

Two related bugs in the same code: `test_anthropic_key` is **defined twice** in `llm_service.py` (lines 40 and 60); the second definition wins, so the live code path is the one with the `print()` calls and the model pinned to `claude-haiku-4-5-20251001`. And `anthropic_provider.py:42` raises `ProviderAuthError` for *generic* failures, so `routes_execute.py:95-96` turns every Anthropic timeout or rate-limit into a 401 "invalid key" for the user (tracked separately as L6, and already noted in `BUGS.md` on the `cleanup/codebase` branch).

**Remediation.** Never return upstream exception text to the client. Log it server-side with a correlation id and return a fixed string:
```python
except ProviderError as exc:
    request_id = uuid4().hex
    logger.exception("provider failure", extra={"request_id": request_id})
    raise HTTPException(502, detail=f"Upstream provider error (ref {request_id})")
```
Replace the two `print()` calls with `logger.warning(...)` that logs `type(e).__name__` only, not `str(e)`. Delete the dead first `test_anthropic_key`. Add a redaction filter to the logging config that scrubs `sk-`, `sk-ant-`, and `AIza`-prefixed tokens as defence in depth. (The `cleanup/codebase` branch already removes both `print()` calls and the duplicate function — landing that branch resolves half of this finding.)

---

## M2 — MEDIUM: passwords longer than 72 bytes cause an unhandled HTTP 500 on register and login

**Evidence**

`backend/app/schemas/auth.py:5`
```python
password: str = Field(min_length=8, max_length=128)
```
`backend/app/utils/security.py:4-8`
```python
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
```
`backend/requirements.txt:5` — `bcrypt==5.0.0`

Verified against the installed library:
```
$ python3 -c "import bcrypt; bcrypt.hashpw(b'a'*100, bcrypt.gensalt())"
ValueError: password cannot be longer than 72 bytes, truncate manually if necessary
```

**Why it matters concretely.** The schema accepts up to 128 characters, but modern `bcrypt` (4.x and 5.x) refuses anything over 72 bytes instead of silently truncating the way `passlib` did. So a user who follows good advice and picks a long passphrase gets an opaque HTTP 500 from `/auth/register` (`routes_auth.py:26`), with the exception surfacing as a server error rather than a validation message. Note also that non-ASCII characters count as multiple bytes, so a 40-character password with emoji or CJK text can trip the same limit. If such an account ever *were* created, `/auth/login` would 500 too (`routes_auth.py:36`), locking the user out permanently. This is a correctness and availability bug rather than a compromise of the hash, but it is in the authentication path and it fails loudly in production.

Note that `passlib==1.7.4` is pinned in `requirements.txt:36` but is never imported anywhere — the README (line 54) credits "bcrypt / passlib"; only raw `bcrypt` is used.

**Remediation.** Pick one and be explicit:
- Cap at the algorithm's real limit — `password: str = Field(min_length=8, max_length=72)` — and validate on bytes, not characters: `len(password.encode()) <= 72`. Simple, but rejects legitimate long passphrases.
- Or pre-hash before bcrypt so any length works: `bcrypt.hashpw(base64.b64encode(hashlib.sha256(pw.encode()).digest()), bcrypt.gensalt())`. Apply it identically in `verify_password`; this changes the stored hash format, so it needs a migration or a dual-verify path.
- Or move to Argon2id (`argon2-cffi`), which has no length limit and is the current preference for new work.

Either way, wrap the calls so a `ValueError` becomes a 400, never a 500. Also drop the unused `passlib` pin.

---

## M3 — MEDIUM: no rate limiting or lockout on login; registration enumerates accounts

**Evidence**

`backend/app/api/routes_auth.py:30-39` — `/auth/login` has no throttle, no failed-attempt counter, no lockout, no CAPTCHA, and no delay. The user model (`models/user.py`) has no `failed_attempts` or `locked_until` column.

`backend/app/api/routes_auth.py:24-25`
```python
if get_user_by_email(db, creds.email):
    raise HTTPException(status_code=409, detail="Email already registered")
```

**Why it matters concretely.** The login handler correctly returns an identical `"Invalid email or password"` for both unknown-user and wrong-password (`routes_auth.py:35,37`) — good — but `/auth/register` gives the answer away for free: 409 means the address has an account, 201 means it does not. An attacker walks a list of addresses through `/auth/register` to build a target list, then walks passwords through `/auth/login` at whatever rate the network allows. With an 8-character minimum and no lockout, offline-quality guessing rates are available online. bcrypt's work factor (default cost 12) is the only brake, and that also means each guess costs *your* server ~100ms of CPU — so the same endpoint is a cheap CPU-exhaustion vector.

**Remediation.** Rate-limit `/auth/login` and `/auth/register` per IP and per email (e.g. 5 attempts / 15 min, then exponential backoff). For enumeration: make registration respond 201 regardless and send a "you already have an account" email out of band, or accept the trade-off consciously and at least rate-limit the probe. Consider requiring 12+ characters and checking against a breached-password list (`zxcvbn` or the HIBP k-anonymity API).

---

## M4 — MEDIUM: SQLite on an ephemeral filesystem

**Evidence**

`backend/app/config.py:7`
```python
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./promptbox.db"
```
No Postgres driver is present in `requirements.txt` (no `psycopg`, `psycopg2`, or `asyncpg`). `README.md:50,180` documents SQLite as the database.

**Why it matters concretely.** Render's container filesystem is ephemeral unless a persistent disk is explicitly attached. If the deployed backend is running on the default — and nothing tracked in the repo says otherwise, because there is no `render.yaml` — then every deploy, restart, or instance replacement destroys all registered users and all saved prompt versions, with no error and no signal. That is an availability and integrity failure, and it is invisible until a user complains that their history vanished. Separately, SQLite's single-writer lock makes concurrent writes from multiple Uvicorn workers a source of `database is locked` errors under any real load. The falsy-`or` pattern has the same empty-string hazard described in C1.

**Remediation.** Provision Render Postgres, set `DATABASE_URL` to its connection string, add `psycopg[binary]` to `requirements.txt`, and make the variable required (drop the `or` fallback, same as C1). Introduce Alembic before the switch and delete the inline `ALTER TABLE` at `main.py:11-18`, which will not behave the same way on Postgres. If SQLite must stay for now, attach a Render persistent disk and point `DATABASE_URL` at a path on it. **Before migrating, fix H2** — a Postgres `DATABASE_URL` in a developer's `.env` plus a `pytest` run is exactly the data-loss scenario.

---

## M5 — MEDIUM: production backend URL hardcoded in every frontend module

**Evidence** — six independent copies of the same constant:
```
frontend/src/api/client.js:1        const API_BASE = "https://promptbox-9d83.onrender.com";
frontend/src/api/executeApi.js:1    const API_BASE = "https://promptbox-9d83.onrender.com";
frontend/src/api/exportApi.js:1     const API_BASE = "https://promptbox-9d83.onrender.com";
frontend/src/api/versionsApi.js:1   const API_BASE = "https://promptbox-9d83.onrender.com";
frontend/src/api/templatesApi.js:1  const API_BASE = "https://promptbox-9d83.onrender.com"
frontend/src/components/Login.jsx:8 const API_BASE = "https://promptbox-9d83.onrender.com";
```

**Why it matters concretely.** There is no way to point the app at a local backend without editing source. So a developer who runs `npm run dev`, opens `localhost:5173`, pastes a **real OpenAI/Anthropic/Gemini key** into the key field (`ModelSelector.jsx:140`) and clicks Validate is sending that key to the *production* Render host, not to their own machine — and the production host will `print()` any resulting Anthropic error into shared logs (M1). The same applies to passwords typed into the local login form (`Login.jsx:48`). The frontend test files already assume `http://localhost:8000` (`frontend/src/test/executeApi.test.js:29`, `api.client.test.js:12`, `vesrionsApi.test.js:20,32`), so those tests are inconsistent with the shipped source today.

**Remediation.** Single source of truth driven by the environment — which is exactly what the unmerged `origin/cleanup/codebase` branch adds:
```js
// frontend/src/api/config.js
export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
```
Import it in all six places, set `VITE_API_BASE` to the Render URL in Vercel's project settings, and default to localhost so a mistake sends traffic to a dev machine rather than to production. (I checked: `VITE_API_BASE` is a URL only. There is no provider API key anywhere in the frontend environment — see "Areas that are clean".)

---

## M6 — MEDIUM: long-lived, non-revocable JWTs; logout is client-side only

**Evidence**

`backend/app/services/auth_service.py:20-25`
```python
def create_access_token(user_id):
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
```
`frontend/src/App.jsx:19` — logout is `onLogout={() => setUser(undefined)}`, i.e. it clears React state and nothing else.

**Why it matters concretely.** The token carries only `sub` and `exp`. There is no `jti` (so no denylist is possible), no `iat` (so you cannot invalidate "everything issued before time T"), and no `aud`/`iss` (so a token minted by any other service sharing the secret would validate here). Once issued, a token is valid for a full 24 hours and **cannot be revoked**: a user who logs out, or whose laptop is stolen, or whose password you reset, still has a working credential until it expires on its own. Your only revocation lever today is rotating `JWT_SECRET`, which logs out every user simultaneously. `README.md:183` claims "Tokens are short-lived" — 24 hours is not short-lived.

Note the deprecated `datetime.utcnow()`; use `datetime.now(timezone.utc)`.

**Remediation.** Shorten the access token to 15–30 minutes and add a refresh token stored server-side (a row you can delete) or a `jti` denylist keyed in Redis. Include `iat`, `jti`, `iss`, and `aud` in the payload and verify `aud`/`iss` in `jwt.decode` (`dependencies/auth.py:19`). On logout, call a `/auth/logout` endpoint that revokes the refresh token / adds the `jti` to the denylist. Correct the README claim.

*Positive note, deliberately:* the token is held only in React state (`App.jsx:8`) and passed as a prop. There is **no** `localStorage`, `sessionStorage`, or `document.cookie` usage anywhere in `frontend/src` — I grepped for all three and got zero hits. That means a successful XSS cannot simply read the token out of storage, and it means a page refresh logs the user out. That is a genuinely better default than the usual `localStorage.setItem('token', ...)`; if you later add "remember me", prefer an `HttpOnly; Secure; SameSite=Strict` cookie over moving the token into `localStorage`.

---

## LOW findings

**L1 — Interactive API docs exposed in production.** `backend/app/main.py:20` — `FastAPI(title="PromptBox API")` leaves `docs_url="/docs"`, `redoc_url="/redoc"`, and `openapi_url="/openapi.json"` at their defaults, so `https://promptbox-9d83.onrender.com/docs` is a public, browsable, *executable* map of the API — including a Try-It-Out button for the unauthenticated `/api/execute` and `/api/validate-key` (H1). No secrets are in the schema (I checked the committed `backend/docs/openapi.json`; it contains no keys and no URLs). *Fix:* `FastAPI(title=…, docs_url=None, redoc_url=None, openapi_url=None)` when an `ENV`/`RENDER` variable indicates production; keep them on locally. FastAPI itself has no `debug=True` set anywhere, and Uvicorn's `--reload` appears only in the README's local instructions (line 133) — both clean.

**L2 — `/api/templates/*` requires no authentication.** `routes_templates.py:20,30`. The data is a fixed, non-user-specific set of prompt-engineering templates seeded from `seed_templates.py`, so nothing private leaks — but it is an unauthenticated database-touching endpoint with no rate limit, and it will happily serve any row anyone later inserts into the `templates` table. *Fix:* add `Depends(get_current_user)` if templates are meant to be a product feature rather than public content; if they stay public, still rate-limit them.

**L3 — Unhandled `ValueError` on a malformed token subject.** `dependencies/auth.py:32` — `int(user_id)` is outside the `try/except JWTError` block. A validly-signed token whose `sub` is not numeric raises `ValueError` → HTTP 500 rather than 401. Only reachable by someone who can already sign tokens, so the practical impact is small — but it turns into a clean 500-generator under C1. *Fix:* wrap the conversion and raise 401 on failure.

**L4 — `LIKE` metacharacters are not escaped in search.** `routes_versions.py:43-49`:
```python
pattern = f"%{search.lower()}%"
filters = [func.lower(PromptVersion.name).like(pattern), ...]
```
This is **not** SQL injection — `search` is bound as a parameter by SQLAlchemy, and `max_length=255` is enforced at `routes_versions.py:37`. But a user searching for `%` or `_` gets wildcard behaviour they did not ask for, and a query of many `%` characters against a large table is mildly expensive. *Fix:* `search.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')` with `.like(pattern, escape='\\')`.

**L5 — CORS is correctly restrictive, with two notes.** `backend/app/main.py:22-28`:
```python
allow_origins=["http://localhost:5173", "https://prompt-box-seven.vercel.app"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
```
No wildcard origin, and therefore **no wildcard-plus-credentials problem** — this is the dangerous combination and it is not present. Two smaller points: (a) `allow_credentials=True` is unnecessary, because the app authenticates with a Bearer header rather than cookies, and it broadens what a compromised allowed origin can do — set it to `False`; (b) the wildcard methods/headers are harmless here but could be narrowed to `["GET","POST","PATCH","DELETE"]` and `["Authorization","Content-Type"]`. Also worth stating plainly so it is not mistaken for a control: **CORS does nothing to protect H1** — it is a browser-enforced policy, and the unauthenticated endpoints are reachable from any HTTP client. One operational note: Vercel preview deployments get per-branch URLs that this static list will reject.

**L6 — Anthropic provider misclassifies all errors as auth failures.** `anthropic_provider.py:38-42` raises `ProviderAuthError` in the generic `except` branch, where `openai_provider.py:54` and `gemini_provider.py:47` both correctly raise `ProviderError`. Result: every Anthropic timeout, rate-limit, or 500 is reported to the user as HTTP 401 "invalid key" (`routes_execute.py:95-96`), sending them to regenerate a key that was never the problem. Already documented in `BUGS.md` on the `cleanup/codebase` branch. *Fix:* change line 42 to `raise ProviderError(...)`.

**L7 — `model_config` declared outside the class.** `routes_templates.py:12-18` — the `model_config = {"from_attributes": True}` sits at module level, four lines below the end of `TemplateResponse`, so it is a module global rather than Pydantic configuration. It works today only because FastAPI passes `from_attributes=True` itself during response serialization. Not a security issue; fix it so it does not become one if the serialization path changes. Compare `schemas/version_schema.py:23`, which places it correctly inside the class.

---

# Areas that are clean

These were examined specifically and found to be sound. Stating them explicitly so the report is not read as "everything is broken."

**Object ownership / IDOR — clean.** Every handler that reads or mutates a `PromptVersion` filters on `user_id` in the same query as `id`, so an authenticated user cannot reach another user's rows by guessing an integer:
- `routes_versions.py:41` — list: `.filter(PromptVersion.user_id == user.id)`
- `routes_versions.py:59` — read: `.filter(PromptVersion.user_id == user.id, PromptVersion.id == version_id)`
- `routes_versions.py:72-75` — update: same two-predicate filter
- `routes_versions.py:92-95` — delete: same two-predicate filter
- `routes_export.py:41-44` — export: same two-predicate filter

The `user_id` on create comes from the authenticated principal, not from the request body (`routes_versions.py:22` — `user_id=user.id`; `VersionCreateRequest` has no `user_id` field, `version_schema.py:4-11`), so mass-assignment of ownership is not possible either. A missing row returns 404 rather than 403, which also avoids confirming that someone else's id exists. This is the one area of the codebase that is textbook-correct, and the tests back it (`backend/tests/test_search.py:54` exercises cross-user isolation).

**SQL injection — clean.** All queries go through the SQLAlchemy ORM with bound parameters. The only raw SQL in the repository is `main.py:16`, a static DDL string with no interpolation: `text("ALTER TABLE prompt_versions ADD COLUMN tag VARCHAR(32)")`. No f-string ever reaches a `text()` call. No `.execute()` with user input anywhere.

**Frontend XSS — clean.** A grep of all of `frontend/src` and `frontend/index.html` for `dangerouslySetInnerHTML`, `innerHTML`, `document.write`, `new Function`, and `eval(` returns **zero hits**. Model output — the most obviously attacker-influenced string in the product — is rendered as a JSX text child inside a `<pre>`: `ResponseDisplay.jsx:28`, `<pre className="response-card__text">{result.response_text}</pre>`. React escapes it. Template content (`TemplateLibrary.jsx:85`), version names (`VersionSelector.jsx`), and diff output (`DiffView.jsx`) are all text children too. Error messages from the server are rendered as text (`ErrorMessage.jsx:7`, `dashboard.jsx:125`). No `href` is ever built from user or model data, so there is no `javascript:` URL surface either.

**Secrets in git — clean.** Full history scan across all refs (`git log --all --diff-filter=A --name-only`) shows only two commits (`2dc37bb`, `f26fa18`) and no `.env`, `.db`, `.pem`, or credential file was **ever** added. `git ls-files | grep -iE '\.db|\.env|sqlite'` returns nothing. `.gitignore:2` ignores `.env` and its last line ignores `*.db`; `backend/.gitignore:1` ignores `*.db`. Both `.gitignore` files were created in the **initial** commit, so the ordering question does not arise — the database was never tracked and `git check-ignore -v backend/promptbox.db` confirms `backend/.gitignore:1:*.db` matches it. No `.env` file exists on disk at all (`README.md:89` claims "one already exists for development" — it does not, in this checkout). The on-disk `backend/promptbox.db` is 36KB and **empty**: `select count(*) from users` → 0, `select count(*) from prompt_versions` → 0, and a `strings` scan for `sk-`, `sk-ant-`, and `AIza` prefixes finds nothing. No password hashes, no user data, no keys.

*Test fixtures that look key-shaped, checked and confirmed fake:* `backend/tests/test_execute.py:17` (`"sk-test-key"`), `test_execute.py:23` (`"gemini-test-key"`), `backend/tests/test_validate_key.py:15,27` (`"sk-test-valid-key-123"`, `"sk-invalid-key"`), `frontend/src/test/PromptEditor.test.jsx:29,78` (`"sk-test"`), `frontend/src/test/ModelSelector.test.jsx:38` (`"sk-test-key"`), and `token="fake-token"` / `"test-token"` throughout the frontend tests. All are obviously-synthetic placeholders of the wrong length and character class for real credentials, and every provider call in the test suite is mocked (`test_execute.py:32`, `test_validate_key.py:12`). None require rotation. The one thing I would still change: `README.md:104-111` publishes demo credentials `demo@example.com` / `password123` — harmless if that account does not exist on the deployed instance, but worth confirming it does not, since registration is open and anyone reading the repo can try it.

**Provider API keys never reach the frontend bundle — clean.** There is **no** `import.meta.env` or `VITE_` reference anywhere in `frontend/` outside `node_modules` — I grepped `.js`, `.jsx`, and `.html`. There is no `.env` in `frontend/`. So no provider key can be baked into the built bundle, because no build-time variable is read at all. The `cleanup/codebase` branch introduces exactly one: `VITE_API_BASE` in `frontend/src/api/config.js`, which is a base URL, not a credential — safe to land.

**Provider API key data flow — reviewed in full, no persistence.** Keys originate in the browser as user input (`ModelSelector.jsx:137-154`, both inputs correctly `type="password"`), are held in React state only (`dashboard.jsx:14` — `useState({ openai: "", gemini: "", anthropic: "" })`), and are sent to the backend as JSON body fields over HTTPS: `{provider, api_key}` to `/api/validate-key` (`client.js:20-24`), `{prompt, model, api_key}` to `/api/execute` (`executeApi.js:19-23`), and `{prompt, models, api_keys: {openai: …, anthropic: …, gemini: …}}` to `/api/prompt` (`executeApi.js:52-56`). Server-side they are passed straight into the provider constructor (`routes_execute.py:26-32` → `openai_provider.py:16`, `anthropic_provider.py:14`, `gemini_provider.py:16`) and held only on the request-scoped provider instance. **They are never written to the database** — no model has a key column (`models/user.py`, `models/prompt_version.py`, `models/template.py`), **never written to disk** — there is no `open()`/`write()` call anywhere in the backend, and **never echoed back** in any success response (`ExecuteResponse` carries only `model`, `response_text`, `latency`, `execute_schema.py:11-14`). The one residual exposure path is the exception-text handling in M1. Two structural points worth naming even though the code is correct: the keys are sent in a **request body**, not a URL, so they will not land in access logs or `Referer` headers — good; and a key entered on the site is nonetheless trusted to your Render process for the lifetime of the request, which is unavoidable for a server-side relay design but is worth stating in the UI so users know to scope the keys they paste.

**Password hashing — clean (aside from M2).** `utils/security.py:5` uses `bcrypt.hashpw` with a per-password `bcrypt.gensalt()` (default cost 12) and `bcrypt.checkpw` for verification — the correct API, with a real salt, no home-grown hashing, no MD5/SHA1, and no fixed pepper. `models/user.py:11` stores only `hashed_password`. Plaintext passwords are never logged (the grep for `print`/`logger` found nothing in the auth path) and never returned (`routes_auth.py:27,39` return only status/email/token). Login is constant-response for unknown-user vs. wrong-password (`routes_auth.py:35,37`).

**Dependency/build configuration — clean.** `frontend/vite.config.js` is minimal (React plugin + Vitest jsdom config). No `server.proxy`, no `server.host: '0.0.0.0'`, no `server.cors` relaxation, no `define` block injecting build-time constants, no `sourcemap: true` for production. Nothing there exposes a dev server or leaks a secret into the bundle.

---

# AI-generated-output execution: nothing executes model output today

**This is explicit, because it was asked for explicitly: nothing in this repository executes, evaluates, compiles, deserializes, or shells out to anything — model output, user input, or otherwise.**

Backend grep across all `*.py` (excluding `__pycache__`) for `eval(`, `exec(`, `subprocess`, `os.system`, `popen`, `compile(`, `pickle`, `importlib`, `__import__`, `shell=True`, `yaml.load`, and `marshal` returned exactly three hits, all false positives:

| Hit | Verdict |
|---|---|
| `backend/app/main.py:16` — `conn.execute(text("ALTER TABLE …"))` | SQL DDL, static string, no interpolation. Not code execution. |
| `backend/app/api/routes_auth.py:11` — `re.compile(r"^[^@\s]+@…")` | Regex compilation of a static literal. Not code execution. |
| `backend/tests/test_security.py:3` — `def test_hash_is_not_plaintext()` | Matched only on the substring `exec` inside a test name. |

Frontend grep across all of `frontend/src` and `index.html` for `eval(`, `new Function`, `dangerouslySetInnerHTML`, `innerHTML`, and `document.write` returned **zero hits**.

Model output takes exactly one path through the system: provider SDK → `response_text` string → `ExecuteResponse` → JSON → React state (`dashboard.jsx:17`) → rendered as an escaped text child in a `<pre>` (`ResponseDisplay.jsx:28`), optionally copied to the clipboard (`ResponseDisplay.jsx:2-4`), downloaded as a `text/plain` Blob (`ResponseDisplay.jsx:7-15`), or persisted as an opaque string column (`prompt_version.py:17`) and re-serialized on export (`routes_export.py:12-32`). At no point is it parsed as code, interpolated into a shell command, or passed to a template engine. **The current attack surface for generated code is zero.**

---

# Forward-looking: what sandboxed auto-execution will require

The owner flagged a pivot toward sandboxed auto-execution of AI-generated code. This section is design-level guidance to have *before* that code exists, not a review of code that does. The single most important framing: **treat model output as hostile input from an untrusted third party**, because prompt injection means an attacker who controls any text in the context window effectively controls what the model emits, and therefore what your sandbox runs.

**Isolation boundary.** The decision that determines everything else. A Python `exec()` with a restricted `__builtins__` is not a sandbox and has never been one — the escapes are well-known one-liners. A container is the practical floor, and a container alone is not enough for arbitrary attacker-controlled code: run it with a hardened runtime (gVisor, Firecracker microVM, or a per-execution Kata container), non-root user, read-only root filesystem, `--cap-drop=ALL`, `--security-opt=no-new-privileges`, a seccomp profile, and no Docker socket mounted anywhere near it. Managed options exist — E2B, Modal, Cloudflare Workers/Durable Objects, Fly Machines, AWS Lambda — and buying this boundary is almost always the right call over building it. **One sandbox instance per execution, destroyed afterwards**, never a long-lived worker that runs code from multiple users: reuse is how one user's execution reads the next user's output.

**Network egress.** Default deny, outbound. This is the control that prevents the sandbox from being turned into an exfiltration channel or an SSRF pivot. If generated code needs network access, allowlist specific destinations and block the cloud instance-metadata endpoints (`169.254.169.254`, `metadata.google.internal`) explicitly and by IP, plus all RFC1918 ranges and loopback — otherwise generated code reads your Render/AWS instance credentials in one HTTP call. Note that this is a *sharper* problem for PromptBox than for most: your users paste live provider API keys into this application (M1, and the "clean" data-flow note above), so a sandbox with egress plus any path to those keys is a direct credential-theft machine.

**Filesystem.** No mount of the host filesystem, ever. A `tmpfs` scratch directory with a hard size cap (e.g. 64MB), read-only everything else, and no access to the application's own source, `.env`, or database file. Nothing the sandbox writes should be readable by the next execution.

**Resource limits.** Every one of these must be enforced by the runtime, not by cooperative code inside the sandbox: wall-clock timeout (start at 5–10s), CPU quota, memory cap with a hard OOM kill, process/thread count (`pids-limit`, so a fork bomb terminates the container rather than the host), max output bytes (an infinite print loop otherwise fills your disk or your response buffer), and a cap on concurrent sandboxes per user *and* globally. Kill on breach, do not warn.

**Authentication and cost.** Whatever you build here must be behind `get_current_user` from day one — do not repeat H1, where the expensive endpoints ended up public. Rate-limit executions per user, meter them, and set a global concurrency ceiling so one user cannot consume the whole pool.

**Result handling.** Output from the sandbox is untrusted input all over again: cap its size, never render it with `innerHTML` (the current `<pre>{...}</pre>` pattern in `ResponseDisplay.jsx:28` is the right one — keep it), and if you ever render generated HTML, do it in a separate sandboxed `<iframe>` on a *different origin* with `sandbox="allow-scripts"` and a restrictive CSP, never inline in the app's own origin where it would inherit access to the user's session and their pasted API keys.

**Auditing.** Log every execution with the user id, a hash of the code, resource consumption, and exit status, and retain it. When something does escape or gets abused, this is the only record of what ran.

**Sequencing.** Fix C1 and H1 before this feature ships. An auto-execution endpoint reachable with a forgeable token, or one that inherits the current "no auth on the expensive endpoints" pattern, converts every issue above from a contained risk into an anonymous one.

---

## Suggested order of work

1. **C1** — set and rotate `JWT_SECRET`, remove the fallback, delete the default from the README. Nothing else matters until this is done.
2. **H2** — fix `conftest.py` before anyone points `DATABASE_URL` at a real database.
3. **H1** — put `get_current_user` on the three LLM endpoints, add rate limits, bound `prompt` and `models`.
4. **M4** — migrate to Postgres (after H2), with Alembic.
5. **M1, M2, M5** — land `origin/cleanup/codebase` (it already removes the `print()` leaks and centralizes `API_BASE`), then finish the error-detail redaction and the bcrypt length handling.
6. **M3, M6, L1** — login throttling, token lifetime and revocation, disable `/docs` in production.
7. Remaining LOW items as hygiene.
