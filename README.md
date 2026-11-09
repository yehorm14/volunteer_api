# Volunteer Task Manager

A task manager for volunteer coordinators, with optional GPT-4o-mini helpers for categorising tasks and turning notes into tasks.

![Dashboard showing five tasks grouped by status](docs/images/dashboard.png)

## Why it is useful

- Keeps volunteer assignments in one place instead of scattered notes.
- Each account sees only its own tasks.
- Free-text notes become a structured task in one step.

## Features

- Register and log in with email and password (bcrypt hashes, JWT bearer tokens).
- Create, view, edit and delete tasks with `pending`, `in_progress` and `completed` status.
- Dashboard with status counts, filter tabs and optimistic updates that roll back on failure.
- Ownership checks on every task route; another user's task returns 404.
- AI categorise: one-word category and short explanation for a task.
- AI extract: saves a task parsed from free-text notes using structured output.
- AI is optional: without `OPENAI_API_KEY` those two endpoints return 503 and the UI shows a notice.

## How it works

- React app (Axios) calls a FastAPI app split into `auth`, `tasks` and `ai` routers.
- SQLAlchemy stores users and tasks in SQLite, or Postgres via `DATABASE_URL`.
- The OpenAI client is created on first use, so the API starts without a key.

## Tech stack

- Backend: Python 3.13, FastAPI, SQLAlchemy, python-jose, bcrypt, Pydantic v2
- Frontend: React 18, TypeScript, Vite, Tailwind CSS, React Router
- Data and AI: SQLite, OpenAI `gpt-4o-mini`
- Tooling: pytest, GitHub Actions

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cp .env.example .env   # set SECRET_KEY (required); OPENAI_API_KEY is optional
uvicorn backend.main:app --reload
```

In a second terminal:

```bash
cd frontend && npm ci && npm run dev
```

Open `http://localhost:5173`. The API runs on port 8000 with docs at `/docs`. Data is stored in `backend/volunteer.db`. Environment variables and deployment are in [docs/DEPLOY.md](docs/DEPLOY.md).

## Tests

43 tests: `python -m pytest`. The frontend check is `cd frontend && npm run build`.

## Limitations

- No migrations (tables are created at startup) and no frontend tests.
- AI endpoints are tested with a mocked OpenAI client only.

## Licence

MIT. See [LICENSE](LICENSE).
