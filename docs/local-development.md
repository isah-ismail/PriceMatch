# Local development setup

Status: documentation draft for existing components; commands have not been executed as part of this change. No API or frontend exists to start.
Baseline: `f53cb3c`.

## Prerequisites

- Git.
- Python 3.9+ as stated in existing documentation; exact team-supported version remains open.
- PostgreSQL 17, running locally, with psql and createdb on PATH.
- Access to external daily CSVs only if exercising daily-data joins.

Use a new checkout directory. The currently attached local workspace may be an empty Git repository; do not clone over existing work.

## Windows / PowerShell

```powershell
git clone https://github.com/ayseozmen/PriceMatch.git PriceMatch
Set-Location PriceMatch
git switch docs/week1-integration

python --version
psql --version
createdb --version

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r ".\Data Collection & Processing Team\scrapers\requirements.txt"
```

No virtual-environment activation is required with these explicit executable paths.

The scraper uses Python's zoneinfo. Verify timezone support:

```powershell
.\.venv\Scripts\python.exe -c "from zoneinfo import ZoneInfo; print(ZoneInfo('Europe/Istanbul'))"
```

If timezone data is unavailable, install `tzdata` into the virtual environment and repeat the check. This is an environment setup recommendation, not a change to committed dependencies.

Configure connection values to match your installation:

```powershell
$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGUSER = "postgres"
createdb pricematch_db
.\.venv\Scripts\python.exe ".\Database & Backend Development Team\scripts\run_migrations.py"
psql -d pricematch_db -c "\dt"
psql -d pricematch_db -c "SELECT version FROM schema_migrations;"
```

Use an authorized local PostgreSQL role and a password prompt or PostgreSQL password file. Do not commit credentials. If the database already exists, inspect it before proceeding; do not delete or recreate it blindly.

The runner fixes the database name to `pricematch_db`. It finds psql on PATH, then falls back to a Homebrew path. Put the correct tools on PATH; no source edit should be needed. It applies each pending migration and records it in one transaction. Run it a second time to confirm an already-applied migration is skipped.

Expected schema: categories, brands, products, retailers, offers, price_history, schema_migrations.

## macOS / Linux equivalents

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r "Data Collection & Processing Team/scrapers/requirements.txt"
export PGHOST=localhost
export PGPORT=5432
export PGUSER=your_local_role
createdb pricematch_db
.venv/bin/python "Database & Backend Development Team/scripts/run_migrations.py"
psql -d pricematch_db -c '\dt'
```

Install and start PostgreSQL using your platform's supported process. Package-manager commands are intentionally not prescribed.

## Optional offline grocery join check

Provide the actual external Datas directory:

```powershell
$env:INFLATION_DATAS = "C:\path\to\InflationResearchStudy\InflationItems\Datas"
.\.venv\Scripts\python.exe ".\Data Collection & Processing Team\scrapers\specs\marketzade_specs.py" --check
```

`--check` makes no retailer requests and reports latest-file join statistics. It is not a pass/fail test: missing daily files can be logged without a failing process exit code. Review output and source dates.

## Configuration and safety of existing work

- INFLATION_DATAS is read from the process environment. No .env loader exists.
- PostgreSQL CLI tools read PGHOST, PGPORT and PGUSER; use their supported credential mechanisms.
- Existing .gitignore excludes .env and .venv.
- Do not commit the external raw inflation dataset.
- Normal scraper runs update tracked specification CSVs. They are unnecessary for initial database setup.
- Do not save specification CSVs through Excel; identifiers and dates may be reformatted.
- Review `git status` before and after optional component runs.

## Troubleshooting and verification record

Missing psql: add the PostgreSQL bin directory to PATH and reopen the shell. Connection errors: confirm service, host, port, role and database privileges. Missing daily files: verify INFLATION_DATAS and retailer subdirectories. Do not assume default source paths match your machine.

A teammate should record OS, Python/PostgreSQL versions, commands, expected versus actual output and any failures in the Week 1 checklist. No clean-machine setup success is claimed by this PR.
