# PromptBox — CS4398 Group 7

A full-stack prompt engineering workbench that lets users write, execute, version, compare, and export LLM prompts across multiple providers (OpenAI and Google Gemini).

---

## Table of Contents
- [Project Structure](#project-structure)
- [Technologies & Frameworks](#technologies--frameworks)
- [Setup Instructions](#setup-instructions)
- [How to Build & Run](#how-to-build--run)
- [Testing](#testing)
- [Additional Notes for Reviewers](#additional-notes-for-reviewers)
- [API Documentation](#api-documentation)

---

## Project Structure

```
4398_Group7/
├── backend/        # FastAPI application
│   ├── app/
│   │   ├── api/        # Route handlers
│   │   ├── models/     # SQLAlchemy ORM models
│   │   ├── providers/  # OpenAI / Anthropic / Gemini adapters
│   │   ├── schemas/    # Pydantic request/response schemas
│   │   └── services/   # Auth and LLM orchestration
│   ├── tests/          # pytest test suite
│   ├── requirements.txt
│   └── .env            # Environment variables (see below)
└── frontend/       # React + Vite SPA
    ├── src/
    │   ├── components/
    │   ├── pages/
    │   └── api/
    └── package.json
```

---

## Technologies & Frameworks

### Backend
| Technology | Purpose |
|---|---|
| **Python 3.11+** | Primary backend language |
| **FastAPI** | REST API framework |
| **SQLAlchemy** | ORM for database access |
| **SQLite** | Embedded database (no server required) |
| **Uvicorn** | ASGI server |
| **Pydantic** | Request/response validation and serialization |
| **python-jose** | JWT token creation and verification |
| **bcrypt / passlib** | Password hashing |
| **python-dotenv** | Environment variable loading |
| **OpenAI SDK** | OpenAI API integration (`gpt-4o`, etc.) |
| **google-genai** | Google Gemini API integration (`gemini-2.5-flash`, etc.) |
| **Anthropic SDK** | Anthropic API integration (Claude models) |
| **PyTest** | Backend unit and integration testing |

### Frontend
| Technology | Purpose |
|---|---|
| **React 19** | UI framework |
| **Vite** | Build tool and dev server |
| **React Router DOM** | Client-side routing |
| **Vitest** | Frontend unit testing |
| **@testing-library/react** | Component testing utilities |
| **jsdom** | DOM simulation for tests |
| **Vanilla CSS** | Styling |

---

## Setup Instructions

### Prerequisites
- **Python 3.11+** — [python.org](https://www.python.org/downloads/)
- **Node.js 18+** and **npm** — [nodejs.org](https://nodejs.org/)
- API keys for at least one LLM provider 

### 1. Clone the Repository
```bash
git clone https://github.com/shibbirTXST/4398_Group7.git
cd 4398_Group7
```

### 2. Backend Environment Variables

Create a `.env` file inside the `backend/` directory (one already exists for development):

```bash
# backend/.env
DATABASE_URL=sqlite:///promptbox.db
JWT_SECRET=   # required, min 32 chars - generate one, see below
```

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy-compatible database URL | `sqlite:///promptbox.db` |
| `JWT_SECRET` | Secret key used to sign JWT tokens (HS256). Minimum 32 characters. | **Required — no default. The app refuses to start without it.** |
| `ENABLE_API_DOCS` | Serve `/docs`, `/redoc` and `/openapi.json` | `false` (fail-closed) |
| `CORS_ORIGINS` | Comma-separated allowlist of browser origins | `http://localhost:5173,https://prompt-box-seven.vercel.app` |
| `SESSION_COOKIE_SAMESITE` | `strict` \| `lax` \| `none`. Must be `none` while the SPA and API are on different domains. | `none` |
| `SESSION_COOKIE_SECURE` | Send the session cookie over HTTPS only. Required when SameSite is `none`. | `true` |
| `SESSION_COOKIE_NAME` | Session cookie name | `promptbox_session` |
| `ACCESS_TOKEN_TTL_HOURS` | Session lifetime | `24` |
| `RATE_LIMIT_ENABLED` | Master switch for all rate limiting | `true` |
| `LOGIN_RATE_LIMIT_PER_IP` | Login attempts per IP | `10/minute` |
| `REGISTER_RATE_LIMIT_PER_IP` | Registrations per IP | `5/minute` |
| `LLM_RATE_LIMIT_PER_USER` / `..._PER_IP` | Prompt execution limits | `30/minute` / `60/minute` |
| `VALIDATE_KEY_RATE_LIMIT_PER_USER` / `..._PER_IP` | Key-validation limits | `10/minute` / `20/minute` |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth credentials. Set both or neither. | unset (Google sign-in off) |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth credentials. Set both or neither. | unset (GitHub sign-in off) |
| `FRONTEND_URL` | Where the OAuth callback returns the browser. **Required once any provider is configured.** | unset |
| `OAUTH_REDIRECT_BASE_URL` | The API's own public origin, used to build `redirect_uri`. | derived from the request |
| `OAUTH_STATE_TTL_SECONDS` | How long a pending OAuth login stays valid | `600` |
| `OAUTH_PENDING_LINK_TTL_SECONDS` | How long a link awaiting password confirmation stays valid | `600` |
| `FRONTEND_LOGIN_PATH` / `FRONTEND_LINK_PATH` | SPA paths the callback redirects to | `/login` / `/link-account` |

Generate a `JWT_SECRET` with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> **Security:** `JWT_SECRET` has no fallback value by design. Because HS256 is a
> symmetric algorithm, anyone who knows the secret can forge a token for any
> user id — so a default committed to source or documentation would be
> equivalent to having no authentication. The application raises at startup if
> the variable is missing or shorter than 32 characters. Rotating this value
> invalidates every outstanding session.

> **Note:** API keys for OpenAI, Gemini, and Anthropic are provided by the user at runtime through the application UI — they are **not** stored in `.env`.

#### Google and GitHub sign-in

Both providers are optional — PromptBox runs on email/password alone, and the
sign-in screen's provider buttons simply return `503` if their credentials are
absent. A provider with an id but no secret (or the reverse) is a startup
error rather than a login-time one.

Register these callback URLs in the provider consoles. They must match
byte-for-byte, which is what `OAUTH_REDIRECT_BASE_URL` is for:

```
https://<your-api-host>/auth/callback/google
https://<your-api-host>/auth/callback/github
```

Request the **`user:email`** scope for the GitHub app. Without it PromptBox
cannot read the account's primary verified address, and the login is rejected —
it will not fall back to the public profile email, which is neither verified
nor stable.

> **Security:** a provider login is only accepted when the provider reports the
> email address as *verified*. The `state` parameter is carried in a short-lived
> httpOnly cookie and checked before the authorization code is spent. Client
> secrets are used only in the server-side token exchange and never appear in a
> response.

##### What happens when the email already has an account

A verified email proves the person controls the mailbox right now. It does not
prove they are the account holder — mailboxes get recycled, corporate addresses
change hands, and provider accounts get taken over. So the two cases are
treated differently:

| Matched account | What happens |
|---|---|
| **No password set** (created by an earlier OAuth login) | Linked automatically. Both providers have vouched for the same verified address, and there is no credential for the new identity to gain access *around*. |
| **Password set** | Nothing is written and no session is issued. The browser goes to `/link-account`, where the user must enter the existing password. Only then is the `oauth_identities` row created and the session cookie set. |

The parked attempt is a short-lived signed token in an httpOnly, `SameSite=None`
cookie — never in a URL, since it names a specific account and authorises
attaching an identity to it. Confirmation re-reads the account and re-checks
every precondition, so a token cannot outlive an email change or an account
deletion. A wrong password leaves the attempt open to retry; anything else
spends it.

##### Failure handling

The provider legs are browser navigations, so failures redirect to
`FRONTEND_URL/login?auth_error=<code>` rather than serving a page of raw JSON.
The codes are a closed set — `access_denied`, `invalid_state`,
`email_unverified`, `provider_error`, `provider_unavailable`, `link_expired`,
`invalid_password` — and the SPA maps them to sentences in
`frontend/src/oauthErrors.js`. Nothing that varies with user input, provider
output or server state is ever put in the URL, because a URL is written to
browser history, sent in `Referer` headers, and logged by every proxy in
between. The login screen clears the parameter once it has shown the message.

Run the migration after upgrading — OAuth adds the `oauth_identities` table and
makes `users.hashed_password` nullable:

```bash
python -m app.migrations
```

### 3. Test Account

Register an account through the UI — sign-up is open and needs no invite.

> **Note:** this section previously published a shared demo account
> (`demo@example.com` / `password123`). Documented credentials are working
> credentials for anyone who reads the repository, so they have been removed.
> If that account exists on any deployment, delete it. Registration is
> rate-limited and deliberately does not reveal whether an address is already
> taken, so it cannot be used to probe for accounts.

> **LLM API Keys for testing execution:** You will need a valid OpenAI or Google Gemini API key to test live prompt execution. Backend unit tests mock all provider calls and **do not require real API keys**.

---

## How to Build & Run

### Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Create/update the database schema. Required before first run, and after any
# model change. This no longer happens automatically on import.
python -m app.migrations

# Run the development server
uvicorn app.main:app --reload --port 8000
```

The backend API will be available at: `http://localhost:8000`

Interactive API docs are **disabled by default**. Set `ENABLE_API_DOCS=true` in
`backend/.env` to serve `/docs`, `/redoc` and `/openapi.json` locally.

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The frontend will be available at: `http://localhost:5173`

| Variable | Description | Default |
|---|---|---|
| `VITE_API_BASE` | Backend base URL the SPA calls | the deployed Render URL — **set this for local development** |

### Running Both Together

Open two terminal windows and run the backend and frontend commands simultaneously.

> **Important:** the frontend does **not** default to your local backend. `API_BASE`
> (`frontend/src/api/config.js`) falls back to the deployed Render URL, so a local
> `npm run dev` will talk to **production** unless you point it elsewhere. Create
> `frontend/.env.local` with:
>
> ```bash
> VITE_API_BASE=http://localhost:8000
> ```
>
> This matters beyond convenience: without it, any provider API key you paste into
> the local UI is sent to the production backend.

---

## Testing

### Backend Tests

```bash
cd backend
source venv/bin/activate  # if not already active
pytest tests
```

### Frontend Tests

```bash
cd frontend
npm test
```

---

## Additional Notes for Reviewers

- **Database:** SQLite is used for simplicity — no database server setup is required.
  The schema is **not** created automatically: run `python -m app.migrations` from
  `backend/` before the first start and after any model change. (Importing the app used
  to create tables as a side effect, which meant running the test suite could mutate
  whatever `DATABASE_URL` pointed at.)
- **CORS:** Allowed origins default to `http://localhost:5173` and the deployed frontend. Override with the `CORS_ORIGINS` environment variable (comma-separated) rather than editing `backend/app/main.py`. The list must stay explicit: credentialed cookies cannot be used with a wildcard origin, and the allowlist is what gates the CSRF preflight.
- **Template Seeding:** Prompt templates are seeded into the database from `backend/app/seed_templates.py`. Run it once manually if the templates table is empty: `python -m app.seed_templates` from the `backend/` directory.
- **Sessions:** Signing in sets an `httpOnly` session cookie (`promptbox_session`); the
  token is never returned in the response body and page scripts cannot read it. The
  cookie is `Secure` with `SameSite=None`, because the deployed frontend and backend are
  on different domains — see the `SESSION_COOKIE_*` variables above. Sign out with
  `POST /auth/logout`, which clears it server-side.
- **JWT Expiry:** Tokens last **24 hours** (`ACCESS_TOKEN_TTL_HOURS`) and are **not
  revocable** — there is no denylist yet, though tokens carry a `jti` so one can be added.
  If you receive 401 errors after a period of inactivity, log in again.
- **No real API calls in tests:** All backend tests that touch LLM providers use mocks. You can run the full test suite without any API keys.

---

## API Documentation 
**Backend (FastAPI — OpenAPI spec):** set `ENABLE_API_DOCS=true` in `backend/.env`,
start the server, then visit:

- Interactive docs: http://localhost:8000/docs (Swagger UI)
- Alternative view: http://localhost:8000/redoc

These are off unless explicitly enabled, so that a deployment does not publish an
interactive client for its own API. A static copy of the spec is also saved at
`backend/docs/openapi.json`.

**Frontend (JSDoc):** Pre-generated HTML documentation is in `frontend/docs/`. Open `frontend/docs/index.html` in any browser — no server required.