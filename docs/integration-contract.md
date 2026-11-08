# Integration contract and decision register

Status: draft for cross-team review. No schema or algorithm decisions are enacted here.
Baseline: `f53cb3c`, reviewed 2026-11-05.

## Existing source interfaces

| Source | Daily join column | Specification column |
|---|---|---|
| Pozitif | product_id | retailer_product_id |
| Samsung | id | retailer_product_id |
| Beymen | UrunID | retailer_product_id |
| Marketzade, Hakmar, Sariyer, HappyCenter, Ideal | product_name, with source-specific legacy formats | name, resolving to retailer_product_id |

Joins are scoped to a retailer. Existing grocery documentation says names resolving to multiple listing IDs must not be linked. Joining daily prices to retailer listings is distinct from matching products across stores.

Electronics specification fields are defined by `SPEC_FIELDS`; groceries use `GROCERY_FIELDS` in [common.py](../Data%20Collection%20%26%20Processing%20Team/scrapers/specs/common.py). Both include retailer, listing ID, name, brand, category, URLs, attributes and first/last seen dates. Electronics additionally include model and variant details; groceries include barcode and size.

Existing CSV readers use UTF-8 with BOM support. Preserve IDs and barcodes as strings. Specification first/last seen values are dates in Europe/Istanbul; they are not the price observation timestamp.

## Candidate mapping: requires approval

| Source concept | Existing database location | Unresolved point |
|---|---|---|
| retailer | retailers | Stable source-to-retailer lookup |
| retailer_product_id | offers.retailer_product_id | Requiredness and uniqueness |
| name | products.name / offers.retailer_product_name | Canonical versus retailer name ownership |
| model_code | products.model | Whether meaning and length are sufficient |
| barcode | products.barcode | Validation, conflicting evidence, empty string versus NULL |
| category / TÜİK codes | categories | Canonical mapping and hierarchy |
| url | offers.product_url | Missing URL policy |
| image_url | products.image_url | Provenance and fallback policy |
| price and source date | offers / price_history | Parsing, currency, observation time and deduplication |
| storage, RAM, colour, condition, bundle, size, attributes | No dedicated mapping agreed | Preserve data without inventing a variant representation |

Do not silently drop unmapped fields or assume that one barcode proves product equivalence. Existing documentation warns that image-derived barcodes can be misleading.

## Open decisions

Every item below is **open**. Suggested reviewers identify relevant roles, not confirmed assignees.

| ID | Decision needed | Evidence / risk | Suggested reviewers |
|---|---|---|---|
| INT-01 | Canonical listing identity and uniqueness | Data team specifies retailer + listing ID; schema currently uses retailer + URL uniqueness and nullable listing ID | Data, database/backend |
| INT-02 | Missing or invalid URL handling | Schema requires nonempty URL; daily sources may lack URLs; enrichment sometimes supplies them | Data, database/backend |
| INT-03 | Variant and condition representation | Current schema has model and variant text, without dedicated spec columns | Matching, database/backend |
| INT-04 | Grocery join normalization and ambiguity policy | Existing documentation rejects ambiguous names; legacy formats differ | Data, matching, integration |
| INT-05 | Canonical category mapping | Retailer paths and TÜİK codes differ from canonical categories | Matching/hierarchy, data, database |
| INT-06 | Price parsing, currency and observation time | History defaults to insertion time; source dates may have day-level precision | Data, database/backend |
| INT-07 | Import identity and replay behavior | History has no source-record deduplication constraint | Database/backend, integration |
| INT-08 | Late data, corrections and atomic updates | No importer currently coordinates current price and history | Database/backend, integration |
| INT-09 | Unresolved matching results and provenance | No matching output or confidence/review contract exists | Matching, integration, database |
| INT-10 | Stock and freshness semantics | Nullable in_stock and last_updated exist; missing listings do not prove out-of-stock | Data, backend, frontend |
| INT-11 | API request/response and error contracts | No API implementation or specification exists | Backend, frontend, integration |
| INT-12 | Supported runtime and reproducible dependencies | Python minimum is documented; scraper dependencies use lower bounds | Component owners, integration |

## Proposed contract acceptance process

For each decision, record alternatives, chosen behavior, approving roles, date and affected documents. Until approved, keep it open. Capture sample valid, invalid, missing and ambiguous records with expected handling. Schema changes belong in a separately reviewed new migration; existing migrations must remain intact.

Proposed import reports should distinguish read, accepted, rejected, ambiguous, unresolved and duplicate records, retaining source file and row identity. Exact fields and storage remain open.

This document defines review questions and candidate mappings, not an executable contract.
