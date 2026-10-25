
from pathlib import Path
import shutil
import subprocess
import sys

# PriceMatch database configuration
DATABASE_NAME = "pricematch_db"

# Find the project's migration folder
PROJECT_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = PROJECT_DIR / "database" / "migrations"

# Locate PostgreSQL's command-line tool
PSQL = shutil.which("psql") or "/opt/homebrew/opt/postgresql@17/bin/psql"


def run_sql(sql):
    """Execute SQL and return the result."""
    result = subprocess.run(
        [
            PSQL,
            "-X",
            "-d", DATABASE_NAME,
            "-v", "ON_ERROR_STOP=1",
            "-t",
            "-A",
            "-c", sql
        ],
        text=True,
        capture_output=True,
        check=True
    )
    return result.stdout.strip()


def main():
    print("PriceMatch Database Migration Runner")
    print("------------------------------------")

    # Check that the migration folder exists
    if not MIGRATIONS_DIR.is_dir():
        raise FileNotFoundError(
            f"Migration directory not found: {MIGRATIONS_DIR}"
        )

    # Ensure the migration tracking table exists
    tracking_file = MIGRATIONS_DIR / "000_migration_tracking.sql"

    subprocess.run(
        [
            PSQL,
            "-X",
            "-d", DATABASE_NAME,
            "-v", "ON_ERROR_STOP=1",
            "-f", str(tracking_file)
        ],
        check=True
    )

    # Read migrations that have already been applied
    applied = set(
        run_sql(
            "SELECT version FROM schema_migrations;"
        ).splitlines()
    )

    # Find migration files in numerical order
    migration_files = sorted(
        path for path in MIGRATIONS_DIR.glob("*.sql")
        if path.name != "000_migration_tracking.sql"
    )

    for migration in migration_files:
        version = migration.stem

        # Skip migrations that have already been applied
        if version in applied:
            print(f"Already applied: {version}")
            continue

        print(f"Applying migration: {version}")

        # Read the SQL migration file
        sql = migration.read_text(encoding="utf-8")

        # Apply migration and record it in one transaction
        safe_version = version.replace("'", "''")

        transaction_sql = (
            "BEGIN;\n"
            + sql
            + "\nINSERT INTO schema_migrations (version) "
            + f"VALUES ('{safe_version}');\n"
            + "COMMIT;\n"
        )

        subprocess.run(
            [
                PSQL,
                "-X",
                "-d", DATABASE_NAME,
                "-v", "ON_ERROR_STOP=1",
                "-f", "-"
            ],
            input=transaction_sql,
            text=True,
            check=True
        )

        print(f"Successfully applied: {version}")

    print("Database migrations are up to date!")


if __name__ == "__main__":
    try:
        main()
    except (
        subprocess.CalledProcessError,
        OSError
    ) as error:
        print(
            f"Migration failed: {error}",
            file=sys.stderr
        )
        sys.exit(1)
