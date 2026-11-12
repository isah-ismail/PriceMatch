# Required-field checklist (Team 01, draft)

This draft sets the checks a product row should pass before matching (Team 02). It started on 2026-10-29 and now uses the delivered columns. Teams 02 and 03 still need to confirm it.

A row missing a **Required** field is set aside. A row missing an **Important** field is sent, but flagged. Column names are in [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

## Fields

| Field | Example | Level | Check |
|---|---|---|---|
| Product name | `Pınar Süt Yarım Yağlı 1 L` | Required | Not empty; original kept next to the cleaned name |
| Price | `42.50` | Required | See price rules |
| Store | `Migros` | Required | One spelling per store |
| Date | `2026-10-29` | Required | Real calendar date, `YYYY-MM-DD` |
| Row identity | `(Beymen, 1865304)`, `IDEAL-000123` | Required | Source ID with its store where one exists, otherwise Team 1 `offer_id` |
| CPI category | `0111211` | Important | 7-digit item code in the CPI list; stored as text |
| Brand | `Pınar` | Important | Confirmed; one spelling |
| Size and unit | `1 L`, `paket` | Important | One written form; ranges are not sizes |
| Pack quantity | `6` | When applicable | From patterns such as `6 x 200 ml` or `6'lı` |
| Variant | `laktozsuz` | When applicable | Fat level, flavour and similar |
| Colour | `Siyah` | When applicable | Non-food products |
| Storage | `256` | When applicable | Number in GB |
| Model code | `MG8Q4TU/A` | When applicable | Part number; text |
| Barcode | `8690698515713` | When available | Text |
| Product link | `https://…` | When available | `http` or `https` with a hostname. This does not prove the link works |
| Image | `https://…` | When available | Same syntax check |

"When applicable" means an empty value is not an error if the field does not fit the product, such as storage on a cable.

CPI category was Required in the first draft. It moved to Important because 26,723 of 99,375 delivered grocery records have no valid code.

## Price rules

| Price | Action |
|---|---|
| Missing | Set aside and report as missing |
| Cannot be read as a number | Set aside and report as unreadable |
| Zero | Set aside and report as zero |
| Negative | Set aside and report as negative |
| 999, 9999 or another round value | Keep. Flag for review only when store evidence suggests an error value |

Read each price in its source format: SozSanal uses a decimal comma. Prices are in TL.

## Extra fields by product type

Two products are the same only if these fields also agree.

| Product type | Expected beyond the required fields | Example |
|---|---|---|
| Food and drink | Brand, size and unit, pack quantity, variant | `Efes Pilsen 50 cl Kutu, 6'lı` |
| Personal care | Brand, size and unit, shade or model code | `Flormar Oje 112, 11 ml` |
| Electronics | Brand, model code, storage, colour, condition | `Apple iPhone 18 256 GB Siyah` |
| Clothing | Brand, product type, colour | `H&M Spor Ayakkabı Beyaz` |
| Home and furniture | Brand, model name, dimensions, colour | `IKEA METOD 60x60 cm Beyaz` |

## Where the delivered data stands

Rows and stages differ, so columns do not add up to one total. Evidence and row reconciliation are in [the audit report](data/audit/week1_audit_report.md).

| Check | Grocery catalog | Beymen specs | Pozitif specs |
|---|---:|---:|---:|
| Rows | 99,375 | 13,144 | 1,334 |
| Row identity missing | 0, but 127 rows have `record_key` only | 0 | 0 |
| Brand empty, cleaned files | 19,982 | 6,638 | 9 |
| Size and unit empty | 12,064 | Not measured | Not measured |
| CPI category empty, cleaned files | 26,723 | 4,513 | 1,334 |

Pozitif's daily file has 130 rows with price 0, all marked as bundles in its spec file, so they fail the price check.

## To confirm

**Team 02 (Iftikhar, Poyraz)**

- [ ] Are these fields enough to decide that two listings are the same product?
- [ ] Should a row missing brand or size reach matching flagged, or be held back?

**Team 03 (Fatima, Yake Kamal)**

- [ ] Are the column names in [DATA_DICTIONARY.md](DATA_DICTIONARY.md) acceptable?
- [ ] Should CPI category stay Important, or become Required for category pages?
