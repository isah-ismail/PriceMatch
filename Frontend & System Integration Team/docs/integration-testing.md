# Initial integration testing strategy

Status: proposed strategy. This plan extends the existing backend test suite to cover cross-team integration.

## Existing evidence

The database README reports manual PostgreSQL 17 checks for table creation, offers, comparison, history, constraints and migration reruns. It says temporary records were rolled back. The [backend suite](../../Database%20%26%20Backend%20Development%20Team/backend/README.md) covers health, product endpoints and catalogs. The [workflow](../../.github/workflows/backend-tests.yml) runs pytest on SQLite and PostgreSQL 17 for changes matching its backend/database paths. Its PostgreSQL tests use ORM metadata, so they do not replace a migration-runner check. Existing grocery --check commands report statistics, not reliable automated assertions.

## Scope and isolation

Week 1 prepares contracts, test cases, fixture definitions and ownership. Use a disposable PostgreSQL 17 instance and small deterministic fixtures; do not run tests against a shared or production database. The current runner hardcodes pricematch_db, so isolate the server/instance until configurable test targeting is separately approved.

Required PR checks should eventually be offline. Live retailer checks should be optional, scheduled or manual, respect existing access rules, and report external failures separately.

## Test matrix

| ID | Boundary | Case and expected result | Availability |
|---|---|---|---|
| MIG-01 | Migrations | Fresh isolated DB creates six domain tables plus tracking | Existing runner; automation proposed |
| MIG-02 | Migrations | Second run skips applied migration with unchanged schema | Existing runner; automation proposed |
| MIG-03 | Migrations | A deliberately failing fixture migration leaves no partial migration objects or applied-version row | Future isolated harness; never edit repository migrations |
| DB-01 | Constraints | Invalid foreign keys, nonpositive prices, blank required names and duplicate retailer URLs are rejected | Existing schema |
| DB-02 | Categories | Direct self-parent rejected; document longer-cycle limitation | Existing schema |
| SRC-01 | CSV interface | Both field sets parse with UTF-8 BOM and Turkish text; IDs/barcodes remain strings | Fixture validation proposed |
| JOIN-01 | Electronics | Pozitif product_id, Samsung id and Beymen UrunID resolve only within retailer | Existing documented rules; integration test future |
| JOIN-02 | Groceries | Unique name resolves; duplicate-name and missing-name cases are reported without forced assignment | Existing documented rule; integration test future |
| MAP-01 | Mapping | Fields, NULL/empty values, condition, size and variants follow an approved mapping with no silent loss | Blocked on contract decisions |
| IMP-01 | Import replay | Same source observation imported twice produces agreed deduplicated result | Future importer; INT-07 |
| IMP-02 | Late/corrected data | Older observations and corrections follow approved current-price/history policy | Future importer; INT-08 |
| IMP-03 | Transactions | Injected failure cannot leave inconsistent offer/history state | Future importer |
| API-01 | API | Requests, responses, errors, currency and comparable variants follow approved contract | Existing v1 suite. Cross-team acceptance and contract changes tracked in INT-11 |
| E2E-01 | User journey | Search to product comparison to price history using seeded fixtures | Frontend API integration/backend |

Do not label planned scenarios as passing. Tests of proposed policies become authoritative only after the relevant decisions are approved.

## Proposed fixture catalogue

Create fixtures later in a separately approved test change:
- Electronics: each source ID format, two retailers sharing the same local ID, distinct storage/colour/condition, missing image.
- Groceries: unique name, one name with two listing IDs, missing name, pack-size conflict and uncertain image-derived barcode.
- CSV edge cases: BOM, quoted delimiters, Turkish characters, leading-zero barcode, empty optional values, malformed JSON.
- Prices: valid source amount, invalid/zero/negative amount, duplicate observation, older observation, corrected observation and day-only date.

Use synthetic or small approved samples. Record provenance and expected results; do not copy the raw external dataset.

## Proposed execution and reporting

Keep the current backend workflow. A separate integration check can exercise the SQL runner and approved source contracts against an isolated PostgreSQL 17 database. For a seeded local smoke test, check health, search for a known demo product, then use its returned ID to verify offers and history. Treat empty results as valid when the database has no demo data.

Report test ID, commit, environment, fixture version, expected/actual result and defect link. Component owners review boundary expectations; integration coordinates the matrix. Named owners remain to be assigned.

Week 1 exit: reviewers accept the matrix and fixture plan, setup evidence is recorded, open decisions are visible, and planned checks are clearly separated from executed evidence.
