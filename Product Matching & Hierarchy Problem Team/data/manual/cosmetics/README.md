# Manual comparison set: Cosmetics & Personal Care (Yake)

**Category:** Cosmetics and Personal Care (TÜİK COICOP 13, sub-codes 1312xxx)
**Comparisons completed:** 250 (file `cosmetics_pairs_manual.csv`)
**Shops:** Gratis, Watsons, Rossmann
**Labelled on:** 20 November 2026

## Source files

All three stores come from the class repository `urazkagangunes/InflationResearchStudy`
(branch `master`), folder `InflationItems/Datas/13_Personal_Care/Cosmetics/`:

| Shop | File | Rows | Unique names |
|---|---|---|---|
| Gratis | `Gratis/gratis_2026-11-20.csv` | 13,203 | 13,203 |
| Rossmann | `Rossmann/rossmann_2026-11-20.csv` | 9,092 | 8,833 |
| Watsons | `Watsons/watsons_2026-11-20.csv` | 9,553 | 8,118 |

Each file has only four columns: `product_name, price, category_number, sub_category_number`.
There is no brand, barcode, size or URL column, so every comparison is based on the product name.

## How the 250 pairs were built

1. `build_candidates.py` normalises names (Turkish-aware lower-casing, `gr` → `g`, `&amp;` cleanup),
   parses the size (ml / g / adet / multi-packs such as `4x150g`) and takes the first word as a brand block.
2. For every product it scores the same-brand products of the other store with RapidFuzz
   `token_set_ratio` and keeps the top 3 above 55.
3. From these candidates it samples 250 pairs, stratified so the set is not only easy matches:
   40 % with similarity ≥ 90, 40 % between 72 and 90, 20 % below 72, spread over the
   TÜİK sub-categories and over the three store pairs
   (Gratis–Watsons 100, Gratis–Rossmann 75, Watsons–Rossmann 75).
4. Every pair was then read and labelled by hand. The script only picks *what* to compare; it does
   not decide the label.

Run: `python build_candidates.py <folder with the three CSVs> candidates.csv 2026-11-20`

## File format

`cosmetics_pairs_manual.csv` follows the phone set (`../phone_pairs_manual.csv`) with the store
names made explicit, since three stores are involved:

| Column | Meaning |
|---|---|
| `pair_id` | `COS-001` … `COS-250` |
| `shop_a`, `name_a`, `price_a` | first store, its product name and price in TRY on 20 Nov 2026 |
| `shop_b`, `name_b`, `price_b` | second store |
| `manual_label` | `same` = identical product (brand, line, variant/shade/scent, size, pack); otherwise `different` |
| `confidence` | `high` / `medium` / `low` — how sure the label is from the names alone |
| `manual_reason` | one-line justification |
| `size_a`, `size_b` | size parsed from the name (empty when the name has none) |
| `tuik_sub_a`, `tuik_sub_b` | TÜİK sub-category code from the source rows |
| `name_similarity` | RapidFuzz token-set score used for candidate selection (not a label) |

Labelling rule: a pair is `same` only when brand, product line, variant (shade number, scent,
flavour), size and pack count all agree or are clearly abbreviated versions of each other.
A size, shade, scent or pack difference makes it `different`, as in the phone guideline
(colour and storage differences = different). When one store's name is too generic to confirm the
line (for example "Neutrogena Temizleme Mendili 25 Adet"), the label is `different` with
`confidence = low`, so those rows can be excluded from scoring if needed.

## Result summary

| | Gratis–Watsons | Gratis–Rossmann | Watsons–Rossmann | Total |
|---|---|---|---|---|
| same | 20 | 20 | 17 | 57 |
| different | 80 | 55 | 58 | 193 |

* Confidence: 224 high, 14 medium, 12 low (`COS-010, 016, 023, 069, 075, 123, 137, 180, 192, 200, 217, 220`).
* Name similarity alone is a weak signal here: 50 of the 193 `different` pairs score ≥ 90, while
  7 of the 57 `same` pairs score below 90. Most high-score non-matches differ only in a number
  (shade 402 vs 404, 50 ml vs 100 ml, 2 vs 4 pieces) or a single variant word (Sensitive vs
  Extra Sensitive, EDT vs EDP).
* Among the 57 identical products, Gratis was the cheaper store in 34 cases, Watsons in 16,
  Rossmann in 6.

## Issues found

1. **No identifiers.** The cosmetics price files have no barcode, brand or retailer product id,
   so matching must rely on names. The phone sets had model codes; this category does not.
2. **Price formats differ.** Watsons stores prices as text (`"419,90 ₺"`), Gratis and Rossmann as
   numbers (`419.9`). The script converts Watsons prices; the shared cleaner should do the same.
3. **Duplicate names.** Rossmann (259) and Watsons (1,435) repeat product names on the same day,
   sometimes with different prices; the script keeps the first occurrence.
4. **Generic names.** Some stores drop the product line ("Dove Sıvı Sabun Nemlendirici 450 ml",
   "Neutrogena Temizleme Mendili 25 Adet"), which makes an exact decision impossible from the name.
5. **Numbers carry the meaning.** Shade numbers, sizes, pack counts and SPF values decide most
   labels. A matcher needs to extract and compare them explicitly; token similarity treats
   `402` and `404` as nearly identical strings.
6. **Spelling and encoding noise.** `&amp;`, `Tıraş/Traş`, `Framboise/Framboisse`, `Depply/Deeply`,
   `gr` vs `g`, and Turkish `İ/ı` casing all appear and need normalisation before comparison.
7. **Category drift.** Laundry capsules, diapers, sunglasses and a smart scale appear under the
   cosmetics sub-codes (e.g. 1312023), and Rossmann has 199 rows with sub-category `0`.
8. **Variant words with no shared vocabulary.** "Parlak Mükemmellik" vs "Parlak Beyaz",
   "Çiçeksi Ferahlık" vs "Çiçeksi Kokular": stores translate or rename the same line differently.
