# Week 3 Integration Defect & Issue Tracker

**Author:** System Integration, Testing & Deployment (Ayşe Özmen)  
**Date:** 17-18 November 2026  
**Status:** Open for Team Review & Component Owner Action

---

## Active Defects (Reported to Component Teams)

| Issue ID | Severity | Component | Summary | Impact | Recommended Action / Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DEF-01** | **Critical** | Backend ORM (`models.py`) | `Offer` model does not reflect Migration 002: missing `listing_id` and `condition`. | Backend cannot store or query the new unique `listing_id` or offer condition (`new`, `display`, `used`). | Add `listing_id` and `condition` attributes to `Offer` class in `models.py`. (Backend Team / Yake) |
| **DEF-02** | **Critical** | Backend API (`schemas.py` & `models.py`) | `product_url` is non-nullable (`str`) in `schemas.py` and `nullable=False` in `models.py`, whereas Migration 002 explicitly made `product_url` nullable (`DROP NOT NULL`). | Any store listing imported without a URL causes `500 Internal Server Error` (Pydantic ValidationError) when queried. | Update to `product_url: str | None = None` in `schemas.py` and `nullable=True` in `models.py`. (Backend Team / Yake) |
| **DEF-03** | **High** | Backend ORM (`models.py`) | Obsolete `UniqueConstraint("retailer_id", "product_url")` is still present in `Offer.__table_args__`. Migration 002 dropped this constraint. | Multiple variants sharing the same retailer product page URL will cause database crash on insert. | Remove the `UniqueConstraint` from `models.py` and replace with `Index("idx_offers_retailer_source_id", "retailer_id", "retailer_product_id")` and unique index on `listing_id`. (Backend Team / Yake) |
| **DEF-04** | **Medium** | Matching Pipeline ➔ Importer | Product Matching outputs pair comparisons (`product_matches.csv`) instead of a canonical mapping table `(listing_id, canonical_product_id)`. | PostgreSQL importer (`import_week3.py`) still keeps every store listing as a separate product (`product_id`) to avoid bad merges. Offers for identical items are not yet grouped. | Matching team should produce a 3-column CSV: `listing_id, canonical_product_id, confidence`. (Matching Team / Iftikhar & Poyraz) |

---

## Resolved & Closed Issues

- **RES-01:** Scraper path in `local-development.md` corrected to active clean specs (formerly DEF-05).
- **RES-02 (14 Nov):** Scraper and cleaner pipeline duplication merged into single-run scripts by Umut Ayar.
- **RES-03 (14 Nov):** Retailer shortlist reduced from 8 to 3 clean MVP stores (Beymen, Pozitif, Samsung) to prevent data corruption.
- **RES-04 (14 Nov):** Store listing identity separated into `retailer_product_id` (raw) and `listing_id` (unique prefixed) across all clean spec files.
- **RES-05 (16 Nov):** PostgreSQL importer successfully processed and loaded 12,557 listings into the Week 3 database via `import_week3.py`.
