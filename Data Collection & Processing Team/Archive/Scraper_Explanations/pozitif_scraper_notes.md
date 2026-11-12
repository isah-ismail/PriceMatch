How the Pozitif scraper works
In pozitif_specs.py (Data Collection & Processing Team/scrapers/specs/pozitif_specs.py), the script requests products from:
https://www.pt.com.tr/wp-json/wc/store/v1/products
This is an API: an address that returns structured data for programs to read. Instead of finding text inside a visual webpage, the script receives JSON, which contains named fields and lists.
An illustrative product response would look like:
{
    "id": 17870,
    "name": "iPhone 13 128GB ...",
    "sku": "MLPG3TU/A-Teşhir",
    "attributes": [
        {"name": "Renk", "terms": [{"name": "Yıldız Işığı"}]},
        {"name": "Depolama", "terms": [{"name": "128GB"}]}
    ]
}
Its main functions divide the work:
Function	Job
fetch_catalogue()	Download product pages from the API
attribute_map()	Convert the nested attribute list into simpler name–value pairs
category_path()	Build a readable category path
to_spec()	Convert one API product into your standard CSV record
main()	Coordinate the whole process
The API returns up to 100 products per request. The script requests page 1, then page 2, and so on. This is pagination—the same idea as moving through search-result pages.
It waits one second between pages and stops when it reaches the final page or an empty response, with a safety limit of 100 pages.
The transformation maps store terminology into your columns:
Renk             → color
Depolama         → storage_gb
Bellek           → ram_gb
Ekran Boyutu     → screen_size_in
Ürün Durumu      → condition
It also standardizes values:
"128GB"     → 128
"1 TB"      → 1024
"Teşhir"    → "display"
"İkinci El" → "used"
An actual saved example is:
retailer_product_id: 17870
model_code: MLPG3TU/A
color: Yıldız Işığı
storage_gb: 128
condition: display
Notice that the original SKU’s -Teşhir suffix is removed from model_code, while condition is stored separately. That lets the project recognize the underlying model without losing the fact that this listing is a display unit.
