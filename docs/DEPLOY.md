# Configuration and deployment

## Environment variables

Backend variables go in a `.env` file at the repo root (see `.env.example`). The file is read when the app starts, not when tests run.

| Variable | Required | Default |
| :--- | :--- | :--- |
| `SECRET_KEY` | yes | none; the API refuses to start without it, or with `change-me` or a key under 16 characters |
| `OPENAI_API_KEY` | no | AI endpoints return 503 |
| `DEMO_USER_EMAIL`, `DEMO_USER_PASSWORD` | no | unset; when both are set, a demo user with sample tasks is created at startup (password at least 8 characters) |
| `DATABASE_URL` | no | SQLite file at `backend/volunteer.db`; `postgres://` and `postgresql://` URLs work (both are run through the psycopg2 driver) |
| `AUTO_MIGRATE` | no | `1`: the API applies pending migrations at startup. Set `0` to run `python -m backend.migrate` yourself |
| `CORS_ORIGINS` | no | local dev origins (`localhost:5173`, `localhost:3000`); comma-separated, trailing slashes are ignored |
| `VITE_API_URL` | production builds (frontend) | `/api` (Vite proxy) in dev only; a production build without it shows a configuration error |

Generate a secret key with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

## Deploy

- API on Render: `render.yaml` defines the service. Set `CORS_ORIGINS` to the frontend URL; `SECRET_KEY` is generated.
- Frontend on Vercel: set the project root to `frontend` and add `VITE_API_URL` with the API URL. It is read at build time, so redeploy after changing it. `vercel.json` rewrites all routes to `index.html`.

SQLite on Render's free tier is ephemeral. Point `DATABASE_URL` at a Postgres database to keep data. CI runs the migrations and an authenticated task flow, including an app restart, against a real Postgres 16 server.

## Task status contract and legacy data

Valid statuses are `pending`, `in_progress` and `completed` (`backend/task_status.py`, mirrored in `frontend/src/types/index.ts`; a test keeps them in sync). The API returns 422 for anything else, for a null or blank `title`, and for a null `status`.

Rows written before this contract may hold other values. When migrating, the repair rewrites them in place and never deletes a task: known spellings (`In Progress`, `done`, `todo`, ...) map to the canonical value, and anything unrecognised or NULL becomes `pending`. Migration `0002` applies this repair and then adds `NOT NULL` on `title`/`status` and a `CHECK` constraint on `tasks.status`. A task that still carries an unrecognised status shows an "Unknown status" badge in the dashboard and can be reset to pending from its card.

## Database migrations

Schema changes are versioned with Alembic (`backend/migrations/versions`):

| Revision | What it does |
| :--- | :--- |
| `0001` | Initial schema: `users` and `tasks`, exactly what the app created itself before migrations existed |
| `0002` | Repairs legacy task rows, then enforces the status contract (see above) |

```bash
python -m backend.migrate          # upgrade to the latest revision (safe to repeat)
python -m backend.migrate --check  # exit 1 if the database is behind
```

Both commands use `DATABASE_URL` (and read `.env`). The API runs the same upgrade at startup unless `AUTO_MIGRATE=0`.

### Existing installations

A database created by an older version has the `users` and `tasks` tables but no `alembic_version` table. `python -m backend.migrate` recognises that, checks that the expected columns exist, records it as revision `0001` without touching any data, and then applies `0002`. If the tables are present but do not look like the original schema, it stops with an error and changes nothing, so you can inspect the database.

### Backup and rollout for a hosted deployment

1. Back up first: `pg_dump --format=custom --file=backup-$(date +%F).dump "$DATABASE_URL"` (on Render, also take a manual backup from the database dashboard). Keep it until the new version has run cleanly.
2. Optionally rehearse on a copy: restore the dump into a scratch database and run `DATABASE_URL=<scratch url> python -m backend.migrate`.
3. Deploy with a single API instance, or set `AUTO_MIGRATE=0` and run `python -m backend.migrate` once from a shell or release step before starting more instances, so two instances never migrate at the same time. With the default `AUTO_MIGRATE=1` the first instance to start applies the migrations.
4. Check `python -m backend.migrate --check` exits 0, then sign in and open the dashboard to confirm the tasks are there.
5. Deploy the frontend after the API.
6. Rollback: Postgres runs each migration in a transaction, so a failed upgrade leaves the database unchanged. To go back after a successful upgrade, redeploy the previous API version and restore the backup (`pg_restore --clean --dbname "$DATABASE_URL" backup.dump`); anything written since the backup is lost. `alembic downgrade` is implemented for `0002` but does not undo the status repair.
