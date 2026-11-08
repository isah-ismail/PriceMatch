# Local development setup

These steps cover the existing components at upstream commit `202b03a`. They were reviewed against the repository. A clean environment run remains a review task.

Use Python 3.12 for the backend, PostgreSQL 17, and Git. Put `psql` and `createdb` on PATH. Start from the repository root in a checkout of the review branch or current upstream.

## Windows PowerShell

```powershell
python -m venv .venv
$python = (Resolve-Path ".\.venv\Scripts\python.exe").Path
$backend = ".\Database & Backend Development Team\backend"
& $python -m pip install -r "$backend\requirements.txt"

$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGUSER = "postgres"
createdb pricematch_db
& $python ".\Database & Backend Development Team\scripts\run_migrations.py"

Set-Location $backend
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Create the database only if absent. Adjust the role and connection settings for your own PostgreSQL instance. If `.env` already exists, keep it and edit its values as needed. Set `DATABASE_URL` to the same local database in `.env` before starting the backend.

```powershell
& $python -m uvicorn app.main:app --reload
```

Open [interactive API docs](http://127.0.0.1:8000/docs) and check [health](http://127.0.0.1:8000/health). Search can return an empty list on a newly migrated database.

## macOS and Linux

Use the same repository-relative paths and database steps. From the repository root, create the venv with `python3.12 -m venv .venv`, install backend dependencies with `.venv/bin/python -m pip install -r "Database & Backend Development Team/backend/requirements.txt"`, and run the migration script with `.venv/bin/python "Database & Backend Development Team/scripts/run_migrations.py"`. Change to the backend directory, copy `.env.example` to `.env` if absent, and start with `../../.venv/bin/python -m uvicorn app.main:app --reload`.

## Optional demo and component checks

- From the backend directory, run `python scripts/seed_demo_data.py --days 14 --datas <path>` using the activated backend environment or the explicit venv executable. Supply the actual inflation study `Datas` directory. Seed only a dedicated local demo database. The loader refuses a populated database without `--reset`, which replaces existing demo contents.
- Run `python -m pytest -q` from the backend directory with the same environment. It defaults to SQLite. For PostgreSQL, set `TEST_DATABASE_URL` to a disposable test database. The test suite creates and drops ORM tables in that database. Use a dedicated empty database.
- Install the separate [scraper requirements](../../Data%20Collection%20%26%20Processing%20Team/scrapers/requirements.txt) if needed. Set `INFLATION_DATAS` for the grocery scripts' offline `--check`; a missing input can be logged without a failing exit status. Normal scrapes update tracked CSVs. If `ZoneInfo("Europe/Istanbul")` fails on Windows, install `tzdata` in the environment.
- Keep credentials and raw inflation-study data local. Backend settings can use `.env`, while scraper configuration reads the process environment.

See the [backend README](../../Database%20%26%20Backend%20Development%20Team/backend/README.md) and [database README](../../Database%20%26%20Backend%20Development%20Team/database/README.md). The migration runner resolves `psql` on PATH and targets `pricematch_db`. Its applied-version query is `SELECT version FROM schema_migrations;`.
