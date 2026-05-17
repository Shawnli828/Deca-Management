# Management Table Cloud Deploy

This app is cloud-ready in a simple setup:

- Frontend: `index.html`
- Backend: `server.py`
- Database: Postgres in the cloud via `DATABASE_URL`
- ReelFarm key: server-side env var `REELFARM_API_KEY`

## Recommended Setup

Use Railway for the fastest team deployment because it can host the Python web service and Postgres database in one project.

Render also works with the included `Procfile` and `requirements.txt`.

## Required Environment Variables

Set these in your cloud web service:

```text
DATABASE_URL=postgresql://...
REELFARM_API_KEY=rf_...
```

Do not put `REELFARM_API_KEY` in frontend code.

## Start Command

```bash
python server.py
```

The server automatically uses:

- `PORT` from the cloud provider
- `0.0.0.0` host in cloud
- Postgres when `DATABASE_URL` is present
- local SQLite when `DATABASE_URL` is absent

## Import Current Local Data

The current local products were exported to `seed_data.json`.

After the cloud service has `DATABASE_URL`, run this once in the provider shell:

```bash
python scripts/import_seed.py
```

## Health Check

After deploy, open:

```text
https://YOUR-APP-URL/api/health
```

Expected:

```json
{"ok": true, "database_backend": "postgres"}
```

Then open:

```text
https://YOUR-APP-URL/
```
