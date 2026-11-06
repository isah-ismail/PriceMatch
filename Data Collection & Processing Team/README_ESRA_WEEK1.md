# Esra's Week 1 contribution

This package holds Esra's Week 1 work for Team 01 (Data Collection & Processing). It covers 27 stores and 8 spec files in detail, plus an inventory of 373 inflation data folders. It does not include raw data, Umut's work, cleaned datasets, matching proposals or database exports.

## Where it goes

These files belong in `Data Collection & Processing Team/` in `isah-ismail/PriceMatch`. At commit `f53cb3cd75e3ae3ce2abca7d265080b2ac592103`, no file in this package has the same path as an existing file.

## Week 1 tasks and evidence

| Task | Evidence | Status |
|---|---|---|
| Load and inspect sample files | [schema_summary.csv](data/audit/schema_summary.csv), [store_inventory.csv](data/audit/store_inventory.csv) | Done; 373 folders are inventory only |
| List fields and types | [field_inventory.csv](data/audit/field_inventory.csv) | Done for the 27 stores and 8 spec files |
| Find missing values, duplicates and inconsistent formats | [Audit report](data/audit/week1_audit_report.md) sections 3–6, [electronics_quality_stats.csv](data/audit/electronics_quality_stats.csv) | Done; links checked for syntax only |
| Compare store schemas | [Audit report](data/audit/week1_audit_report.md) section 3 | Done for the 27 stores and 8 spec files |
| Draft the data dictionary | [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Draft; needs Team 02 and 03 confirmation |

## Files

| File | Purpose |
|---|---|
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Column meanings, types and ID definitions |
| [REQUIRED_FIELD_CHECKLIST.md](REQUIRED_FIELD_CHECKLIST.md) | Draft checks before matching |
| [data/audit/week1_audit_report.md](data/audit/week1_audit_report.md) | Findings, scope and limits |
| [data/audit/store_inventory.csv](data/audit/store_inventory.csv) | One row per inflation data folder |
| [data/audit/schema_summary.csv](data/audit/schema_summary.csv) | One row per reviewed source |
| [data/audit/field_inventory.csv](data/audit/field_inventory.csv) | One row per reviewed field |
| [data/audit/electronics_quality_stats.csv](data/audit/electronics_quality_stats.csv) | Electronics checks per store |
| [data/audit/summary.json](data/audit/summary.json) | All audit results in one file |
| [scrapers/audit/build_week1_audit.py](scrapers/audit/build_week1_audit.py) | Rebuilds the CSV and JSON files |

## External inputs

These inputs are not in this package.

| Option | Input | Repository | Input last changed in |
|---|---|---|---|
| `--datas` | Required. `InflationItems/Datas` | `urazkagangunes/InflationResearchStudy` | See the commit below |
| `--cpi` | Default: `Inflations/Codes/product-to-ctagory/tuik_cpi_categories_comma.csv`, found from `--datas` | `urazkagangunes/InflationResearchStudy` | `b610dd173` |
| `--specs` | `data/specs` | `esraseezgin/cimri-akakce-team1` | `670d457` |
| `--clean` | `data/specs_clean` | `esraseezgin/cimri-akakce-team1` | `1c36c7f` |
| `--stores` | `data/groceries/pricematch/stores` | `esraseezgin/cimri-akakce-team1` | `f4df7c2` |

### Exact versions used

| Repository | Branch | Commit |
|---|---|---|
| `esraseezgin/cimri-akakce-team1` | `main` | `3058728f123ff8598ab76c942d33840da597ecd5` |
| `urazkagangunes/InflationResearchStudy` | `master` | `b56bb5aced66b7128f32e4fbe25df998ab3de967` |

**Uncommitted inputs: none.** The three `cimri-akakce-team1` input folders match that commit. The 27 reviewed daily files and the CPI list are tracked at the inflation commit, with no local changes.

**Package files:** they are newer than commit `3058728`. In `cimri-akakce-team1`, they are on `main` in the commit that adds this README.

The script needs Python 3.9 or later and no extra packages. It was tested with Python 3.13.

## Run

Run from this folder. Replace the two paths with your local copies. `--out` keeps the delivered audit files untouched.

```bash
python scrapers/audit/build_week1_audit.py --datas "<InflationResearchStudy>/InflationItems/Datas" --specs "<cimri-akakce-team1>/data/specs" --clean "<cimri-akakce-team1>/data/specs_clean" --stores "<cimri-akakce-team1>/data/groceries/pricematch/stores" --out "audit_rebuild"
```

Use the commits above to reproduce the numbers. Beymen's `data/specs/beymen_specs.csv` in PriceMatch commit `f53cb3c` differs from the file used here. The script reads your local copy, so a newer inflation checkout can change the results.

## Limits

- Links were checked for syntax only; none was opened.
- Section 2 of the report cites grocery catalog and export files that stay in `cimri-akakce-team1`.
- `DATA_DICTIONARY.md` describes those external files too. They are not part of this package.
