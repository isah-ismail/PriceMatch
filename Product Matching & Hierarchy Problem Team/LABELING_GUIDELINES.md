# Labeling guidelines

These rules define the manually verified reference dataset used to evaluate every matching algorithm in this module.

## The file

`data/labels/pairs_to_label.csv` holds 440 pairs of listings from two different retailers. Each row is one pair. Fill in the `label` column and, where useful, the `note` column. Do not change any other column.

Save the finished file as `data/labels/pairs_labeled.csv`, as CSV (UTF-8), so the unlabeled original stays reproducible.

## The question to answer

> If a shopper saw these two listings side by side, would comparing their prices be fair?

## Labels

| Label | Meaning | Price comparison |
|---|---|---|
| `same` | The identical product: same brand, same product, same variant, same size and pack count, same condition | Fair |
| `comparable` | The same product line, but something a shopper pays for differs: size, pack count, flavour, colour, storage, or condition | Not fair directly |
| `different` | Different products | Not meaningful |
| `unsure` | The names and product pages do not give enough information to decide | Excluded from scoring |

## Rules

1. **Judge from the names first, then the product pages.** Open `url_a` and `url_b` when the names leave doubt.
2. **Different wording is not a difference.** Word order, abbreviations, spelling, upper or lower case and extra descriptive words do not change the label. `İçim Süt Rahat Laktozsuz 1 Lt` and `İçim Laktozsuz Süt 1Lt` are `same`.
3. **Size and pack count must agree for `same`.** `250 g` against `500 g`, or a single item against a pack of six, is `comparable`. Units written differently (`1 Lt`, `1 L`, `1000 ml`) are equal.
4. **Flavour, scent, fat level and colour are part of the product.** Strawberry against cocoa wafer of the same line is `comparable`.
5. **Electronics: storage, memory, screen size, colour and model code must agree for `same`.** A `256GB` phone against the `512GB` version is `comparable`.
6. **Condition matters.** A display (`Teşhir`), outlet or used unit against a new unit is `comparable`.
7. **Different brands are `different`**, even for the same kind of product.
8. **A missing detail is not a difference.** If one name gives the size and the other does not, check the product page. If the page does not settle it, use `unsure`.
9. **Do not guess.** `unsure` is a valid answer and is better than a wrong label.

## How the pairs were chosen

`build_labeling_pairs.py` draws pairs from six groups so the set contains likely matches, near misses and clear non-matches. Barcodes and model codes were used only to choose which pairs to show. They are not shown as an answer, they are never given to the matching algorithms, and they do not replace the human decision: two listings with the same barcode can still be labeled `comparable` or `different` if the listings disagree.

The `sampling_group` column records which group each pair came from. Ignore it while labeling.

## How the labels are used

- `same` is the positive class. `comparable` and `different` are the negative class. `unsure` pairs are left out of the metrics and reported as a count.
- The split into training and test data is made by product, not by pair, so a product never appears on both sides.

## Limits to state in the report

- One person labeled the data, so agreement between labelers is not measured.
- The pairs were sampled on purpose to include hard cases, so the share of matches is higher than in the full catalog. Scores describe performance on this set, not on all possible pairs.
- Sariyer, Ideal, Beymen, Pozitif and Samsung carry no barcodes, so pairs involving them rest on names and product pages alone.
