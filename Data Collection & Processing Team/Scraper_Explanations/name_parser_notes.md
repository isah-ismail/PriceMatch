**How the name parser extracts information**

name_parser.py (Data Collection & Processing Team/scrapers/specs/name_parser.py) is the processing component Beymen uses.

It uses **regular expressions**, often called **regex**: text patterns that recognize things such as “a number followed by GB.”

For example:

MacBook Air 13" M5 ... 24GB Bellek 1TB SSD Gümüş Laptop MDH94TU/A

Its rules interpret the text approximately like this:

|   |   |
|---|---|
|**Text found**|**Interpretation**|
|24GB Bellek|24 GB RAM|
|1TB SSD|1,024 GB storage|
|13"|13-inch screen|
|Gümüş|Colour|
|MDH94TU/A|Apple model code|
|MacBook|Evidence that the brand is Apple|

Storage and RAM need extra care. The parser:

- Treats sizes followed by RAM or Bellek as RAM.
- Tries to skip graphics-card memory.
- For remaining sizes, assumes the largest is storage.
- May treat a smaller size as RAM.

Those last steps are **heuristics**—practical rules that often work, but can make mistakes. They are not verified manufacturer specifications.

There is also an important accessory rule. In:

15" Laptop Kılıfı

the size describes the laptop the case fits. For Beymen’s accessory category, the parser therefore leaves storage, RAM, screen size, and family empty.
