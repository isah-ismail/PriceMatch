# Week 1 summary — Team 01 (Data collection & processing)

Umut (scraping), Esra (cleaning). This page lists where each Week 1 task from the
8-week plan is answered.

## Umut — Scraping

| Task | Where |
|---|---|
| Shared GitHub access | Done: the whole team has access to this repo |
| List the stores and categories | [README.md](README.md): "Where the data comes from" and "What is done" |
| Look at the existing scripts | [Scraper_Explanations/](Scraper_Explanations/): one note per scraper |
| Pick two stores | [RETAILER_SHORTLIST.md](RETAILER_SHORTLIST.md): **Beymen and Pozitif** |
| What each store gives (IDs, links, descriptions) | [README.md](README.md) store table, [scrapers/specs/README.md](scrapers/specs/README.md) |
| How often prices update | [RETAILER_SHORTLIST.md](RETAILER_SHORTLIST.md): "How often prices update" (daily) |

## Esra — Cleaning

| Task | Evidence | Status |
|---|---|---|
| Load and inspect sample files | [schema_summary.csv](data/audit/schema_summary.csv): 27 stores and 8 spec files. [store_inventory.csv](data/audit/store_inventory.csv): 373 folders, inventory only | Done |
| List fields and types | [field_inventory.csv](data/audit/field_inventory.csv): inferred and recommended types | Done for the 27 stores and 8 spec files |
| Find missing values, duplicates and inconsistent formats | [week1_audit_report.md](data/audit/week1_audit_report.md) sections 3–6, [electronics_quality_stats.csv](data/audit/electronics_quality_stats.csv), [grocery report](data/groceries/pricematch/data_quality_report.md) | Done; links checked for syntax only |
| Compare store schemas | [week1_audit_report.md](data/audit/week1_audit_report.md) section 3: 7 schemas | Done for the 27 stores and 8 spec files |
| Draft the data dictionary | [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Draft done; column names need Team 02 and 03 confirmation |

Supporting draft: [REQUIRED_FIELD_CHECKLIST.md](REQUIRED_FIELD_CHECKLIST.md), also waiting for Teams 02 and 03.

## Dataset audit for the MVP stores

[DATA_AUDIT_BEYMEN_POZITIF.md](DATA_AUDIT_BEYMEN_POZITIF.md): column coverage, problems found
and rules for the other teams. Main points:

- **147 products** can be compared at both stores today (203 shared model codes).
- Beymen has **no images**, and its brand and model code come only from product names.
- Pozitif has **130 bundles with price 0** and display/used products that share the new
  product's model code. These must be filtered out.
