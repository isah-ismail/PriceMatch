# Manual comparison set: Dormitories (Accommodation)

**Category:** Restaurants & Accommodation → Dormitories (TÜİK COICOP 11, sub-codes 1120301 / 1120398)
**Comparisons:** 250 (file `dorm_pairs_manual.csv`)
**"Shops" (providers):** Bilkent Üniversitesi, Özyeğin Üniversitesi, Ankara Üniversitesi
**Price date:** 19 November 2026 (latest file in each folder)

## Source files

Read-only, from `InflationResearchStudy/InflationItems/Datas/11_Restaurants/Accommodations/Dormitories/`:

| Provider | File | Rows | Distinc Items | Price basis in source |
|---|---|---|---|---|
| Bilkent | `Bilkent Üniversitesi/Bilkent Üniversitesi_2026-11-19.csv` | 15 | 1120301 | per semester ÷ 4.5 months |
| Özyeğin | `Özyeğin Üniversitesi/Özyeğin Üniversitesi_2026-11-19.csv` | 19 | 1120301 | per academic year ÷ 9 months |
| Ankara | `Ankara Üniversitesi/Ankara Üniversitesi_2026-11-19.csv` | 28 | 1120398 | monthly |

All prices are TRY **per person per month**.

## What counts as the "same product" for a dorm room

The same room cannot be sold by two universities, so here a "product" means a **room specification**:

| Label | Rule | Phone analogy |
|---|---|---|
| `same` | same number of people in the room, same room class, and no stated conflict in bed type or kitchen |
| `comparable` | same number of people, but a different room class (standard / en-suite / suite / studio / partitioned) or a stated conflict (bunk vs normal beds, kitchenette vs none) |
| `different` | different number of people in the room |

These are the rules the script uses. The hand review of the Bilkent–Özyeğin pairs (see
[Result summary](#result-summary)) labelled some class differences `same`: standard vs partitioned 3-person rooms, an en-suite double vs a 2-person suite, and a standard single vs Özyeğin's plain studio. So in 5 `same` rows (DORM-015, 028, 046, 058, 060), `room_type_a` and `room_type_b` differ.

The building, campus, city and gender of the dorm are not part of the product but they are kept in the names.

`confidence`: `high` when both names state the room class and the key features. `medium` when one side leaves something out, for example Ankara's "İki Kişilik Oda" with no "Standart" or "Süit" (taken to be standard), a bed type or kitchen given on only one side, or Ankara "Süit" compared with a Bilkent en-suite room (Ankara doesn't say what its suite includes).

## How the 250 pairs were built

`build_dorm_pairs.py`:

1. Reads the latest dated CSV for each of the three universities.
2. Uses a room specification table that was written by hand after reading every source row
(`ROOM_SPECS` for Bilkent and Özyeğin). Each entry has the occupancy, room class, bed type and kitchen. Ankara's room names all follow one pattern (`<Tek/İki/Üç/Dört/Beş> Kişilik [Standart|Süit] Oda`), so they are parsed. If a new room name turns up, the script stops with a `KeyError` so that it can't be labelled without a spec.
3. Labels every cross-provider pair with the rules above. The script leaves `manual_reason`
empty. The reasons were added afterwards (see [Result summary](#result-summary)).
4. Samples 250 pairs, split across the provider pairs (Bilkent–Özyeğin 84, Bilkent–Ankara 83, Özyeğin–Ankara 83). The target mix is about 32 % same, 30 % comparable and 38 % different.About 60 % of the `different` pairs are hard negatives, where the occupancy differs by only one person. The sampler prefers room pairs it hasn't used yet. Bilkent–Özyeğin has only 14 possible `same` pairs, so all of them are included and the shortfall is made up with `different` pairs. The random seed is fixed (20261120), so the file can be rebuilt exactly.

Run: `python3 build_dorm_pairs.py [<Dormitories folder>] [<output.csv>]`. It needs only the
standard library. With no arguments, it reads the DataScraping folder and writes next to the script.

## File format

The columns are based on the cosmetics set (`PriceMatch/.../data/manual/cosmetics/cosmetics_pairs_manual.csv`):

| Column | Meaning |
|---|---|
| `pair_id` | `DORM-001` … `DORM-250` |
| `shop_a`, `name_a`, `price_a` | first provider, full source `product_name`, monthly price per person (TRY) |
| `shop_b`, `name_b`, `price_b` | second provider |
| `manual_label` | `same` / `comparable` / `different` |
| `confidence` | `high` / `medium` |
| `manual_reason` | one-line justification |
| `occupancy_a`, `occupancy_b` | people per room |
| `room_type_a`, `room_type_b` | standard / ensuite / suite / studio / partitioned |
| `tuik_sub_a`, `tuik_sub_b` | TÜİK sub-category code from the source rows |
| `price_basis_a`, `price_basis_b` | how the source turned the published fee into a monthly figure |

## Result summary

All 250 pairs were reviewed by hand after the script ran, and their labels were corrected where needed. In all 250 pairs, `manual_reason` uses one of four fixed phrases: `Same room specification` (same), `Same occupancy, different room type` (comparable), `Different occupancy` and `Different occupancy, different room type` (different). For `different` pairs, the longer phrase is used exactly when `room_type_a` and `room_type_b` differ. First 61 pairs (DORM-001 … DORM-061) were written by hand. The remaining 189 (DORM-062 … DORM-250) were filled by AI using the same rule and then checked one by one by hand. Hand review made 8 pairs `same` that the script had labelled `comparable`, for example a partitioned 3-person room vs a standard one, or a double with a private bathroom vs a 2-person suite. Re-running the script gives the original, unreviewed labels.

| | Bilkent–Özyeğin | Bilkent–Ankara | Özyeğin–Ankara | Total |
|---|---|---|---|---|
| same | 22 | 27 | 27 | 76 |
| comparable | 17 | 25 | 25 | 67 |
| different | 45 | 31 | 31 | 107 |

* Confidence: 169 high, 81 medium (57 of the 76 `same` pairs are medium, mostly because Ankara doesn't state the room class).
* In matching pairs, Ankara (a public university) is 4–12× cheaper than either private university.
  Bilkent is cheaper than Özyeğin in 18 of the 22 matching pairs.

## Issues found

1. **No product identity across providers.** Rooms can only be matched on specification, not
   identity. Building, campus and city always differ.
2. **Occupancy is written three ways:** words ("Çift/İki Kişilik"), digits ("2 KİŞİLİK"), and codes
   ("2K", "D4S", "STE1"). A matcher must normalise all three.
3. **Different billing periods.** Fees are published per semester (Bilkent), per academic year
   (Özyeğin) or per month (Ankara). The scraper already divides by 4.5 or 9. The divisor is kept in
   `price_basis_*` because it is an assumption.
4. **Unstated room class.** Ankara often omits "Standart". Beykent ("A TİPİ") and İTÜ ("Normal",
   "TİP 1") use internal codes that cannot be matched without the university's floor-plan pages.
5. **The same word means different things.** Özyeğin's "STÜDYO … STANDART ODA" is a single studio,
   not a standard room. "Süit" at Ankara and at Özyeğin probably don't mean the same amenities.
6. **Spelling and casing.** `SUİT`/`SÜİT`, `Kişi Başı`/`Kişi başı`, and all-caps Özyeğin names need
   Turkish-aware lower-casing (`İ→i`, `I→ı`) before comparison.
7. **Two TÜİK sub-codes.** Private universities are coded 1120301 and public ones 1120398, so a
   sub-category filter would drop every Bilkent/Özyeğin–Ankara pair.
