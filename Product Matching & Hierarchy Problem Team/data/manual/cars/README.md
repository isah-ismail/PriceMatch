# Manual comparison set: Cars (Esra)

**Category:** Transport, cars (TÜİK COICOP 07)
**Comparisons completed:** 250 pairs (file `cars_pairs_manual.csv`)
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

The brand files give model, year, version and price. arabam.com files give only the listing title
and the price, so brand, model, year and engine were read from the title.

## How the 250 pairs were built

1. `car_comparison_250.xlsx` lists the 250 cars, one per row, sorted by brand and model.
   Cars of the same brand and model share a group (for example "Toyota Corolla"). "Yeni", "Hybrid",
   "Sedan" and "Hatchback" do not start a new group; "Cross" and electric versions do.
2. Each car was compared with the cheapest other car in its group. These 209 comparisons give 162
   different pairs, because the cheapest car and its partner point at each other.
3. `make_pairs.py` turns the table into pairs and adds 88 more pairs inside the same groups, new-vs-used
   pairs first, to reach 250.
4. 41 cars have no partner: 28 are the only car of their model in the list and 13 listing titles do not
   say which car it is. They appear in the table but not in the pairs.

Run: `python make_pairs.py car_comparison_250.xlsx cars_pairs_manual.csv`

## File format

`cars_pairs_manual.csv` follows the cosmetics set (`../cosmetics/cosmetics_pairs_manual.csv`):

| Column | Meaning |
|---|---|
| `pair_id` | `CAR-001` … `CAR-250` |
| `shop_a`, `name_a`, `price_a` | first car: shop, name or listing title as scraped, price in TRY |
| `shop_b`, `name_b`, `price_b` | second car |
| `manual_label` | `same` = same model, version, year and new/used; otherwise `different` |
| `confidence` | `high` when a difference is visible in the names; `low` when the year or version is missing |
| `manual_reason` | one-line justification |
| `group` | brand and model group |
| `year_a`, `year_b`, `condition_a`, `condition_b`, `version_a`, `version_b` | the values compared |
| `row_a`, `row_b` | row numbers (`No`) in `car_comparison_250.xlsx` |

Labelling rule: a pair is `same` only when model, version, year and new/used all agree. A different
year, engine, trim or new-vs-used makes it `different`. When a listing title does not give the year or
version, the label is `different` with `confidence = low`, as in the cosmetics set, so those rows can be
excluded from scoring.

## Results and limits

- 248 pairs are `different` and 2 are `same`. Most pairs compare a new car with a second-hand one, or two
  second-hand cars of different years, so true matches are rare.
- 45 pairs have `confidence = low`.
- New-car prices are from 2026-10-30 and second-hand prices from 2026-10-13 to 2026-10-15.
- arabam.com titles are free text. Brand, model, year and engine were read from them; mileage was not.
