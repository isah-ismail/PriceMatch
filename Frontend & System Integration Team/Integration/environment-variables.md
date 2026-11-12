# Environment variables

Use this reference with the [local development guide](local-development.md). The FastAPI backend reads settings from the process environment and from a local `.env` in its working directory. Start it from the backend folder so it finds that file. The test runner and data scripts read the variables noted below from the process environment.

## Backend settings

Copy the [backend example file](../../Database%20%26%20Backend%20Development%20Team/backend/.env.example) to `.env` in the backend folder if it does not already exist.

| Variable | Purpose and local example |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy connection URL for PostgreSQL. Use `postgresql+psycopg://USER:PASSWORD@localhost:5432/pricematch_db` with your local credentials. |
| `CORS_ORIGINS` | Comma-separated browser origins, including scheme and port, for example `http://127.0.0.1:5500`. The current default is `*` for local development. Set explicit allowed frontend origins in shared or deployed environments. |
| `DEFAULT_PAGE_SIZE` | Number of results per page by default. The current default is `20`. |
| `MAX_PAGE_SIZE` | Maximum number of results per page. The current default is `100`. |

URL-encode special characters in the username or password before inserting them in the connection URL. Keep the database URL in your ignored local `.env` or the deployment environment's secret settings.

## Tests, migrations and data scripts

| Variable | Where it is read | Purpose |
| --- | --- | --- |
| `TEST_DATABASE_URL` | Backend pytest process environment | Optional. The tests use SQLite when unset. To run with PostgreSQL, point this at a separate empty test database because tests create and drop tables. |
| `PGHOST`, `PGPORT`, `PGUSER` | PostgreSQL command-line tools and migration runner | Set the local connection target, for example `localhost`, `5432`, and `postgres`. The runner targets `pricematch_db`. Enter the password at the terminal prompt. |
| `INFLATION_DATAS` | Demo loader and applicable scraper commands | Optional path to the external inflation study's `Datas` directory. Set it in the shell that runs the script. The demo loader also accepts `--datas`. |

## Sharing configuration safely

- Commit example values in `.env.example`. The repository ignores `.env`.
- Keep credentials and real connection strings out of Git, screenshots, logs, issue comments, and team chat.
- When asking for help, share the variable name and a redacted example such as `postgresql+psycopg://USER:REDACTED@localhost:5432/pricematch_db`.
