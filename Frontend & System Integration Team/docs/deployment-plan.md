# Deployment planning

Status: proposed outline only. No hosting platform, environment, CI/CD workflow or deployment is configured by this change.

## Existing foundation

PostgreSQL 17 schema and a migration runner are available. The runner targets pricematch_db and relies on local psql connection settings. The [backend](../../Database%20%26%20Backend%20Development%20Team/backend/README.md) is an ASGI service with `/health`, `DATABASE_URL` and configurable `CORS_ORIGINS`. Its test workflow exists. Hosting, deployed origins, release artifacts and deployment automation remain open.

## Decisions requiring team agreement

| Topic | Questions | Suggested reviewers |
|---|---|---|
| Hosting and environments | Where will development, staging and production run? Who owns access and cost? | Team, integration |
| Runtime and artifacts | The backend uses Python 3.12. What build process and frontend runtime should staging use? | Backend, frontend |
| Configuration | Which settings are required per environment, and how are they validated? | Component owners, integration |
| Secrets | Which provider stores database credentials and who may access them? | Deployment owner |
| Database operations | Who runs migrations, backups, restore drills and recovery? | Database/backend, deployment owner |
| Data ingestion | How are external files delivered, scheduled, retried and audited? | Data, integration |
| Observability | Which logs, health signals, freshness metrics and alerts are needed? | Component owners |
| Rollback | Which app version and database changes remain compatible? | Backend, database, integration |

No provider or responsible individual is assumed by this document.

## Proposed release checklist for a future implementation

1. Record approved commit, build artifact, runtime versions and environment.
2. Pass applicable tests and review contract or migration changes.
3. Validate configuration and secret availability without printing values.
4. Verify backup and restore readiness before a database-affecting release.
5. Apply reviewed pending migrations using an authorized operator.
6. Deploy the API and any approved frontend artifact. Set the browser origin in CORS_ORIGINS.
7. Run staging smoke checks: health, database connectivity, one comparison and one history query using controlled data.
8. Check error logs and source-data freshness; record release evidence.
9. Request explicit approval before production deployment where required by the team's agreed process.

## Proposed recovery approach

Retain the prior compatible application artifact and document restore procedures. Do not treat reversing SQL as automatically safe: migrations may be irreversible or incompatible with an older application. Decide between forward repair and verified restore with the database owner.

The current migration runner provides ordered transactional application, not a complete deployment or rollback system. Concurrent migration execution, locking and environment-specific database selection require separate review.

Week 1 deliverable: an agreed decision list and proposed runbook, not a deployed service.
