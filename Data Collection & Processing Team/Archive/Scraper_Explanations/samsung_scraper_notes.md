How the Samsung scraper works
Samsung’s script (Data Collection & Processing Team/scrapers/specs/samsung_specs.py) also reads an API, but Samsung organizes the response differently.
It starts with 21 category codes covering phones, tablets, TVs, appliances, and other groups.
Within a category, Samsung returns product families, and each family contains a modelList:
Product family: Galaxy A18
    ├── Blue, 128 GB → one model code
    ├── Silver, 128 GB → another model code
    └── Blue, 256 GB → another model code
A particular sellable version is often called a SKU. Your script makes one CSV row per model/SKU, rather than one row for the entire family.
The important pieces are:
* fetch_families() downloads category results, requesting additional pages if needed.
* to_spec() turns each individual model into a standard record.
* seen remembers model codes already processed, avoiding duplicates when a model appears in multiple categories.
Samsung supplies variant details in fmyChipList. Think of these “chips” as labelled options:
COLOR          → Açık Mavi
MOBILE MEMORY  → 128 GB
TV SIZE        → 65"
Your script maps them into:
color          → Açık Mavi
storage_gb     → 128
screen_size_in → 65
It also converts relative image and product links into complete URLs.
The script leaves RAM and processor empty because this API response does not supply them. An empty field means the scraper has no value for it; it does not mean the device has zero RAM.