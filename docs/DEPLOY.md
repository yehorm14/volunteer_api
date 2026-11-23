# Configuration and deployment

## Environment variables

Backend variables go in a `.env` file at the repo root (see `.env.example`). The file is read when the app starts, not when tests run.

| Variable | Required | Default |
| :--- | :--- | :--- |
| `SECRET_KEY` | yes | none; the API refuses to start without it, or with `change-me` or a key under 16 characters |
| `OPENAI_API_KEY` | no | AI endpoints return 503 |
| `DEMO_USER_EMAIL`, `DEMO_USER_PASSWORD` | no | unset; when both are set, a demo user with sample tasks is created at startup (password at least 8 characters) |
| `DATABASE_URL` | no | SQLite file at `backend/volunteer.db`; `postgres://` and `postgresql://` URLs work |
| `CORS_ORIGINS` | no | local dev origins (`localhost:5173`, `localhost:3000`); comma-separated, trailing slashes are ignored |
| `VITE_API_URL` | production builds (frontend) | `/api` (Vite proxy) in dev only; a production build without it shows a configuration error |

Generate a secret key with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

## Deploy

- API on Render: `render.yaml` defines the service. Set `CORS_ORIGINS` to the frontend URL; `SECRET_KEY` is generated.
- Frontend on Vercel: set the project root to `frontend` and add `VITE_API_URL` with the API URL. It is read at build time, so redeploy after changing it. `vercel.json` rewrites all routes to `index.html`.

SQLite on Render's free tier is ephemeral. Point `DATABASE_URL` at a Postgres database to keep data. The Postgres path has a URL-normalisation test but has not been run against a live database.

## Task status contract and legacy data

Valid statuses are `pending`, `in_progress` and `completed` (`backend/task_status.py`, mirrored in `frontend/src/types/index.ts`; a test keeps them in sync). The API returns 422 for anything else, for a null or blank `title`, and for a null `status`.

Rows written before this contract may hold other values. At startup the API rewrites them in place and never deletes a task: known spellings (`In Progress`, `done`, `todo`, ...) map to the canonical value, and anything unrecognised or NULL becomes `pending`. New databases also get a `CHECK` constraint on `tasks.status`; existing databases are not altered by `create_all`, so they rely on API validation until migrations exist. A task that still carries an unrecognised status shows an "Unknown status" badge in the dashboard and can be reset to pending from its card.
