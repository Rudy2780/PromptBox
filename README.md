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

### 3. Demo / Testing Credentials

For testing the running application, you can register any account through the UI or use these sample credentials after seeding:

```
Email:    demo@example.com
Password: password123
```

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
Interactive API docs (Swagger UI): `http://localhost:8000/docs`

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The frontend will be available at: `http://localhost:5173`

### Running Both Together

Open two terminal windows and run the backend and frontend commands simultaneously. The frontend is pre-configured to communicate with the backend at `http://localhost:8000`.

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

- **Database:** SQLite is used for simplicity — the database file (`promptbox.db`) is created automatically on first run. No database server setup is required.
- **CORS:** The backend is configured to allow requests from `http://localhost:5173` (the default Vite dev server port). If you run the frontend on a different port, update `allow_origins` in `backend/app/main.py`.
- **Template Seeding:** Prompt templates are seeded into the database from `backend/app/seed_templates.py`. Run it once manually if the templates table is empty: `python -m app.seed_templates` from the `backend/` directory.
- **JWT Expiry:** Tokens are short-lived. If you receive 401 errors after a period of inactivity, log in again.
- **No real API calls in tests:** All backend tests that touch LLM providers use mocks. You can run the full test suite without any API keys.

---

## API Documentation 
**Backend (FastAPI — OpenAPI spec):** Start the backend server, then visit: - Interactive docs: http://localhost:8000/docs (Swagger UI) 
- Alternative view: http://localhost:8000/redoc A static copy of the OpenAPI spec is also saved at `backend/docs/openapi.json`.

**Frontend (JSDoc):** Pre-generated HTML documentation is in `frontend/docs/`. Open `frontend/docs/index.html` in any browser — no server required.