# PriceMatch
A recreation of cimri/akakçe

PriceMatch is a course project for comparing the same product across retailers, showing offers and price history.

## Current status

As reviewed on 2026-11-05 at commit `f53cb3c`:
- **Existing:** eight retailer specification scrapers and CSV datasets, shared parsing helpers, PostgreSQL schema, migration tracking and migration runner.
- **External dependency:** daily price CSVs belong to the separate InflationResearchStudy project.
- **Documented manual verification:** database documentation reports local integrity checks; executable automated tests are not committed.
- **Proposed / future:** integrated price imports, canonical product matching, API, frontend, automated integration tests, CI and deployment. The architecture below is a plan, not a running application.

## Repository map

| Directory | Purpose |
|---|---|
| [Data Collection & Processing Team](Data%20Collection%20%26%20Processing%20Team/README.md) | Collection status, retailer coverage, data provenance and team handoffs |
| [Specification scraper guide](Data%20Collection%20%26%20Processing%20Team/scrapers/specs/README.md) | CSV fields, commands and retailer limitations |
| [Database & Backend Development Team](Database%20%26%20Backend%20Development%20Team/database/README.md) | PostgreSQL schema, migrations and reported manual checks |
| Frontend & System Integration Team | Existing placeholder; application implementation is future work |
| Product Matching & Hierarchy Problem Team | Existing placeholder; matching implementation is future work |

Existing team documentation remains authoritative for its component. Collection counts and join rates there are dated observations, not current guarantees.

## Week 1 integration documentation

- [Architecture and Mermaid data flow](docs/architecture.md)
- [Integration contract and unresolved decisions](docs/integration-contract.md)
- [Local development setup](docs/local-development.md)
- [Integration testing strategy](docs/integration-testing.md)
- [Deployment planning](docs/deployment-plan.md)
- [Week 1 deliverables and review checklist](docs/week-1-checklist.md)
- [Contribution and fork-to-upstream workflow](CONTRIBUTING.md)

Start with the local setup guide. There is no frontend or backend application startup command yet.

## Important data boundaries

Electronics daily rows join to specification rows using retailer-specific IDs. Grocery daily rows currently require an unambiguous name lookup within a retailer to recover the listing ID. Cross-retailer product matching is a separate responsibility.

Schema mapping, listing identity, missing URLs, variant preservation and repeat-import behavior remain open team decisions. See the integration contract before implementing an importer.

Do not commit the external inflation study's raw dataset. Avoid saving specification CSVs through spreadsheet software, which can alter identifiers and dates. Existing scraper runs update tracked CSVs; see the component guides before running them.

## Contribution status

The Week 1 branch contains documentation only. Branch protections, CI checks and deployment environments described in these guides are recommendations, not configured functionality. Changes should be reviewed through pull requests; nothing in this documentation authorizes a merge or upstream modification.
