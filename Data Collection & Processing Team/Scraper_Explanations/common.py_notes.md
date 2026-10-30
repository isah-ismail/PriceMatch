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