"""
Configuration — Sarıyer Market scraper

Copied from the inflation study (InflationResearchStudy, commit a107f1664,
InflationItems/Codes/01_Food/Sariyer/config.py). Its output and checkpoint
paths were removed; sariyer_specs.py writes data/specs/sariyer_specs.csv.
"""

BASE_URL = "https://www.sariyermarket.com"

PRODUCT_LIST_URL = f"{BASE_URL}/Catalog/OBAjaxFilterProducts"
CATEGORY_API_URL = f"{BASE_URL}/OBComponents/GetHomePageCategories"

DEFAULT_HEADERS = {
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer":  BASE_URL + "/",
    "Origin":   BASE_URL,
}

REQUEST_DELAY  = 0.7
MAX_RETRIES    = 3
RETRY_BACKOFF  = 2
PAGE_SIZE      = 24
DEFAULT_SORT   = "default"
