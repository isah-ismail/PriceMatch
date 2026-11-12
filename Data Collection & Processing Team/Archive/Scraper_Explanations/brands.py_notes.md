**How brands.py finds a brand in a name**

brands.py (Data Collection & Processing Team/scrapers/specs/brands.py) fills the `brand` column for stores that give no brand: Sarıyer, HappyCenter and İdeal. Hakmar and Marketzade send a brand, and brands.py is only used when theirs is empty.

It is **adapted from Esra's grocery catalogue** (commit dddf328). The brand list in scrapers/specs/brands/ is hers too:

- brands.json: 4,139 brand names
- brand_overrides.json: words to remove because they are not really brands ("ideal", "tuna", "dereotu"), and brands to add ("Dr. Oetker", "Coca-Cola")

**How it works**

1. The name is **folded**: lower case, Turkish letters turned into plain letters, symbols removed.

"Ülker Go Ahead Protein Taco Cips 55 Gr" → "ulker go ahead protein taco cips 55 gr"

This way "ÜLKER", "Ülker" and "ulker" are all the same.

2. It tries the first 4 words, then the first 3, 2 and 1, and takes the **longest** one that is a known brand. Longest first matters: "dr oetker" must win over "dr".

3. If nothing matches at the start, it looks for a known **multi-word** brand anywhere in the name.

4. If nothing is found, the brand is left empty. It never guesses.

**How good it is**

| Store | Brand found |
|---|---|
| Sarıyer | 76% |
| HappyCenter | 79% |
| İdeal | 86% |

To check it, we ran it on Hakmar and Marketzade, where the store's own brand is known: it gave the same brand for 90–96% of products. The products without a brand are mostly ones that have none ("Patates Kg", "Köy Biberi") or small local brands missing from the list.

See [[groceries_overview_notes]].
