**What** **common.py** **does for every scraper**

common.py (Data Collection & Processing Team/scrapers/specs/common.py) contains shared tools so the scripts do not repeat the same code.

It defines:

- The standard CSV columns.
- Network sessions, timeouts supplied by callers, and retries for selected error responses.
- Storage and screen-size conversion helpers.
- Output locations.
- The CSV merge-and-save logic.

The merge behavior is especially useful. Suppose yesterday’s file contains products A and B, and today’s collection contains B and C:

Existing CSV: A, B

New results:    B, C

Saved CSV:    A, B, C

A remains so historical price records can still connect to it. B receives the newly collected fields. C is added.

For an existing product, the code preserves the earliest first_seen and latest last_seen. Other fields are replaced by the incoming record, so a newly empty field can overwrite an older populated value.

The file is first written to a temporary .csv.part file and then moved into place, reducing the chance of leaving a half-written final CSV.
**Grocery helpers**

common.py also has five small tools used by the grocery scrapers ([[groceries_overview_notes]]):

- **GROCERY_FIELDS**: the shorter column list for groceries. `merge_and_save()` takes the column list as an option, so the same merge logic works for both electronics and groceries.

- **barcode()**: keeps a code only if it really is a barcode: 8, 12, 13 or 14 digits with the right **check digit**. The last digit of every barcode is computed from the others, so a random number fails 9 times out of 10. Hakmar's onion code `1036223` and Marketzade's 8-digit shop code `74591012` are not barcodes; `8690698515713` is.

- **image_barcode()**: reads a barcode from an image file name (`.../8690560355218.jpg`, `.../8690504107453-F6DB8.png`), with the same check. Used by Marketzade and HappyCenter.

- **pack_size()**: finds the last pack size in a name: "Pınar Süt 1 L" → `1 L`, "Sütaş Ayran 6x200 ml" → `6x200 ml`, "Focus Havlu 12'li" → `12'li`.

- **check_name_join()**: opens the store's newest daily price file and counts how many names link to exactly one product, to several (ambiguous), or to none. Every grocery script runs it after saving, and `--check` runs only this, without any requests.
