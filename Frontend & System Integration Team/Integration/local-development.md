# Local development setup

This guide starts the existing FastAPI backend and PostgreSQL database from the team repository. Run the checks at the end and record your own setup result.

## Prerequisites

- Git.
- Python 3.12, the version used by backend CI.
- PostgreSQL 17, running locally, with psql and createdb on PATH.
- Access to external daily CSVs only if exercising daily-data joins.

Use a new checkout directory for a clean setup check. If you already have the team repository checked out, use your existing checkout and record its commit.

## 1. Clone and install on Windows (PowerShell)

```powershell
git clone https://github.com/isah-ismail/PriceMatch.git PriceMatch-setup
Set-Location PriceMatch-setup
git rev-parse --short HEAD

python --version
psql --version
createdb --version

python -m venv .venv
$python = (Resolve-Path '.\.venv\Scripts\python.exe').Path
& $python -m pip install -r '.\Database & Backend Development Team\backend\requirements.txt'
```

No virtual-environment activation is required with these explicit executable paths.

## 2. Prepare PostgreSQL

Start PostgreSQL locally. Set the following connection values for your local installation. Run `createdb` only if the database does not already exist:

```powershell
$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGUSER = "postgres"
createdb pricematch_db
& $python ".\Database & Backend Development Team\scripts\run_migrations.py"
psql -d pricematch_db -c "\dt"
psql -d pricematch_db -c "SELECT version FROM schema_migrations;"
```

Use an authorized local PostgreSQL role and a password prompt or PostgreSQL password file. Do not commit credentials. If the database already exists, inspect it before proceeding; do not delete or recreate it blindly.

The runner fixes the database name to `pricematch_db`. It finds psql on PATH, then falls back to a Homebrew path. Put the correct tools on PATH; no source edit should be needed. It applies each pending migration and records it in one transaction. Run it a second time to confirm an already-applied migration is skipped.

Expected schema: categories, brands, products, retailers, offers, price_history, schema_migrations.

## 3. Start the backend and verify it

From the repository root, enter the backend directory and create a local configuration file if needed:

```powershell
Set-Location '.\Database & Backend Development Team\backend'
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env' }
```

Edit `.env` so `DATABASE_URL` points to the same PostgreSQL instance and `pricematch_db` used above. The URL format is `postgresql+psycopg://USER:PASSWORD@HOST:PORT/pricematch_db`. Use your local values. Keep credentials in your local configuration and commit only example values.

```powershell
& $python -m uvicorn app.main:app --reload
```

Open [the health endpoint](http://127.0.0.1:8000/health) in your browser. Expect HTTP 200 with `"status":"ok"` and `"database":"ok"`. Open [the API docs](http://127.0.0.1:8000/docs) to try the product search. An empty result is valid on an unseeded database.

To run the backend tests, stop the server with Ctrl+C and run this from the backend directory:

```powershell
& $python -m pytest -q
```

With `TEST_DATABASE_URL` unset, the suite uses SQLite. For PostgreSQL tests, use a separate empty test database because the tests create and drop tables.

For a frontend check, open `Frontend & System Integration Team/frontend/index.html` and check that the page and its sample products load. The frontend currently uses local sample data.

## macOS / Linux equivalents

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r "Database & Backend Development Team/backend/requirements.txt"
export PGHOST=localhost
export PGPORT=5432
export PGUSER=your_local_role
createdb pricematch_db
.venv/bin/python "Database & Backend Development Team/scripts/run_migrations.py"
psql -d pricematch_db -c '\dt'
```

After migrations, enter `Database & Backend Development Team/backend`, copy `.env.example` to `.env` if needed, and configure `DATABASE_URL` as above. Run `../../.venv/bin/python -m uvicorn app.main:app --reload`. To run tests from the same directory, use `../../.venv/bin/python -m pytest -q`.

## Optional offline grocery join check

From the repository root, install the scraper requirements and provide the actual external Datas directory. On Windows, install `tzdata` in the virtual environment if Python cannot load `Europe/Istanbul`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r '.\Data Collection & Processing Team\scrapers\requirements.txt'
$env:INFLATION_DATAS = "C:\path\to\InflationResearchStudy\InflationItems\Datas"
.\.venv\Scripts\python.exe ".\Data Collection & Processing Team\scrapers\specs\marketzade_specs.py" --check
```

`--check` makes no retailer requests and reports latest-file join statistics. It is not a pass/fail test: missing daily files can be logged without a failing process exit code. Review output and source dates.

## Configuration and safety of existing work

- The backend reads its `.env` from the backend directory and can also use process environment variables. The standalone scraper reads `INFLATION_DATAS` from the process environment.
- PostgreSQL CLI tools read PGHOST, PGPORT and PGUSER; use their supported credential mechanisms.
- Existing .gitignore excludes .env and .venv.
- Do not commit the external raw inflation dataset.
- Normal scraper runs update tracked specification CSVs. They are unnecessary for initial database setup.
- Do not save specification CSVs through Excel; identifiers and dates may be reformatted.
- Review `git status` before and after optional component runs.

## Troubleshooting and verification record

Missing psql: add the PostgreSQL bin directory to PATH and reopen the shell. Connection errors: confirm service, host, port, role and database privileges. Missing daily files: verify INFLATION_DATAS and retailer subdirectories. Do not assume default source paths match your machine.

Each teammate should record their operating system, Python and PostgreSQL versions, commit, commands, results and any blockers in the [Week 1 checklist](week-1-checklist.md). Record only checks that you actually ran.
