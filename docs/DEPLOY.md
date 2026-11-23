# Configuration and deployment

## Environment variables

Backend variables go in a `.env` file at the repo root (see `.env.example`). The file is read when the app starts, not when tests run.

| Variable | Required | Default |
| :--- | :--- | :--- |
| `SECRET_KEY` | yes | none; the API refuses to start without it, or with `change-me` or a key under 16 characters |
| `OPENAI_API_KEY` | no | AI endpoints return 503 |
| `DEMO_USER_EMAIL`, `DEMO_USER_PASSWORD` | no | unset; when both are set, a demo user with sample tasks is created at startup (password at least 8 characters) |
| `DEMO_PUBLIC` | no | unset; set to `1` together with `DEMO_USER_EMAIL` to turn that user into a public, read-only sample workspace (see below). `DEMO_USER_PASSWORD` is then optional |
| `DATABASE_URL` | no | SQLite file at `backend/volunteer.db`; `postgres://` and `postgresql://` URLs work |
| `CORS_ORIGINS` | no | local dev origins (`localhost:5173`, `localhost:3000`); comma-separated, trailing slashes are ignored |
| `VITE_DEMO_ENABLED` | no (frontend) | unset; build with `true` to show the "Try the sample workspace" button (only when the API has `DEMO_PUBLIC=1`) |
| `VITE_API_URL` | production builds (frontend) | `/api` (Vite proxy) in dev only; a production build without it shows a configuration error |

Generate a secret key with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

## Deploy

- API on Render: `render.yaml` defines the service. Set `CORS_ORIGINS` to the frontend URL; `SECRET_KEY` is generated.
- Frontend on Vercel: set the project root to `frontend` and add `VITE_API_URL` with the API URL. It is read at build time, so redeploy after changing it. `vercel.json` rewrites all routes to `index.html`.

SQLite on Render's free tier is ephemeral. Point `DATABASE_URL` at a Postgres database to keep data. The Postgres path has a URL-normalisation test but has not been run against a live database.

## Task status contract and legacy data

Valid statuses are `pending`, `in_progress` and `completed` (`backend/task_status.py`, mirrored in `frontend/src/types/index.ts`; a test keeps them in sync). The API returns 422 for anything else, for a null or blank `title`, and for a null `status`.

Rows written before this contract may hold other values. At startup the API rewrites them in place and never deletes a task: known spellings (`In Progress`, `done`, `todo`, ...) map to the canonical value, and anything unrecognised or NULL becomes `pending`. New databases also get a `CHECK` constraint on `tasks.status`; existing databases are not altered by `create_all`, so they rely on API validation until migrations exist. A task that still carries an unrecognised status shows an "Unknown status" badge in the dashboard and can be reset to pending from its card.

## Public sample workspace

A visitor can look around without an account, a password or an AI key.

1. API: set `DEMO_USER_EMAIL` (for example `demo@example.com`, a made-up address) and `DEMO_PUBLIC=1`. At startup the API creates that user with the three made-up sample tasks from `backend/seed_demo.py` (one pending, one in progress, one completed) and never needs its password, so leave `DEMO_USER_PASSWORD` unset.
2. Frontend: build with `VITE_DEMO_ENABLED=true` (plus `VITE_API_URL`). The landing and sign-in pages then show "Try the sample workspace".
3. Check it: `curl -X POST $API/auth/demo` returns a token; with it, `GET /tasks` lists the three sample tasks and `POST /tasks` answers 403.

How it is isolated: everyone shares the one demo user, but that user is read-only. Creating, editing and deleting tasks and both AI endpoints return 403 for it (also if someone signs in with its password), so visitors cannot change or fill the data, spend AI credits or see anyone else's tasks. Real accounts are separate and unaffected. `POST /auth/demo` returns 404 unless `DEMO_PUBLIC=1`, so nothing is exposed by default. There is no rate limiting; if the API is public, put it behind your host's protection.

Do not point `DEMO_USER_EMAIL` at a real person's account: its tasks would become public. Use a made-up address and the seeded sample tasks only. Before announcing the link, open the dashboard in a private window and confirm the three statuses show and the buttons for changing tasks are gone.
