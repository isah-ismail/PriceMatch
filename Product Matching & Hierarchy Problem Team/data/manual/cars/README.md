# Manual comparison set: Cars (Esra)

**Category:** Transport, cars (TÜİK COICOP 07)
**Comparisons:** 250 pairs, all compared and labelled manually (`cars_pairs_manual.csv`)
**Shops:** Hyundai, Renault and Toyota official price lists (new cars) and arabam.com (second-hand)
**Labelled on:** 21 November 2026

## Source files

All data comes from the class repository `urazkagangunes/InflationResearchStudy`, folder
`InflationItems/Datas/07_Transport/motor_bicyle_car/`:

| Shop | Files | Cars used |
|---|---|---:|
| Hyundai official price list | `Hyundai/hyundai_2026-10-30.csv` | 38 |
| Renault official price list | `Renault/renault_2026-10-30.csv` | 23 |
| Toyota official price list | `Toyota/toyota_2026-10-30.csv` | 23 |
| arabam.com second-hand listings | `akakce_scraper/arabam_verileri_2026-10-13.csv` to `…_2026-10-15.csv`, newest price per listing | 166 |

The brand files give model, year, version and price. arabam.com only gives the listing title and the
price, so I read the brand, model, year and engine from each title myself.

## How I did it

1. I listed the 250 cars in `car_comparison_250.xlsx`, one per row, sorted by brand and model, and put
   cars of the same brand and model in the same group (for example "Toyota Corolla"). "Yeni", "Hybrid",
   "Sedan" and "Hatchback" do not make a new group; "Cross" and electric versions do.
2. I compared each car with the cheapest other car in its group and wrote down why they are or are not
   the same car (column "Why").
3. From these comparisons I made the 250 pairs in `cars_pairs_manual.csv`. Where a group had more cars,
   I also paired them with each other, new vs used first.
4. 41 cars have no pair: 28 are the only car of their model in the list and 13 listing titles do not say
   which car it is. They are in the Excel file but not in the pairs.

## File format

`cars_pairs_manual.csv` follows the cosmetics set (`../cosmetics/cosmetics_pairs_manual.csv`):

| Column | Meaning |
|---|---|
| `pair_id` | `CAR-001` … `CAR-250` |
| `shop_a`, `name_a`, `price_a` | first car: shop, name or listing title as scraped, price in TRY |
| `shop_b`, `name_b`, `price_b` | second car |
| `manual_label` | `same` = same model, version, year and new/used; `comparable` = same model but the year, version or new/used differs ("Similar" in the Excel file); `unsure` = the year or version is missing, so it cannot be confirmed |
| `confidence` | `high` when the details are visible in the names; `low` when the year or version is missing |
| `manual_reason` | short note on why |
| `group` | brand and model group |
| `year_a`, `year_b`, `condition_a`, `condition_b`, `version_a`, `version_b` | the values compared |
| `row_a`, `row_b` | row numbers (`No`) in `car_comparison_250.xlsx` |

Labelling rule: a pair is `same` only when model, version, year and new/used all agree. Two cars of the
same model with a different year, engine, trim or new-vs-used are `comparable`: not the same car, but
their prices can be compared. When a listing does not give the year or version, the pair is `unsure`
(`confidence = low`). These are the labels `compare_algorithms.py` reads: `same` counts as a match,
`comparable` as not the same product, and `unsure` rows are left out of scoring.

## Results and limits

- 203 pairs are `comparable`, 45 are `unsure` and 2 are `same`. Most pairs compare a new car with a
  second-hand one, or two second-hand cars of different years, so exact matches are rare.
- New-car prices are from 2026-10-30 and second-hand prices from 2026-10-13 to 2026-10-15.
- arabam.com titles are free text, and mileage is usually not in the title, so it was not compared.
