"""
Category fetcher — Sarıyer Market
Ana sayfanın header menüsünden slug tabanlı kategori URL'leri çeker.

Copied from the inflation study (InflationResearchStudy, commit
a107f1664, InflationItems/Codes/01_Food/Sariyer/category_fetcher.py). Change:
each category also records its menu `level` (1 = top level), so the spec
scraper can read only top-level categories, which include their subcategories.
"""

import time
import logging
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(config.DEFAULT_HEADERS)
    return session


def fetch_categories(session: Optional[requests.Session] = None) -> list[dict]:
    if session is None:
        session = _make_session()

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = session.get(config.BASE_URL, timeout=30)
            resp.raise_for_status()
            break
        except requests.RequestException as exc:
            if attempt == config.MAX_RETRIES:
                raise RuntimeError(f"Ana sayfa alınamadı: {exc}")
            time.sleep(config.RETRY_BACKOFF * attempt)

    soup = BeautifulSoup(resp.text, "lxml")
    menu_links = soup.select(".header-menu a, .top-menu a, .mega-menu a")

    seen: set[str] = set()
    categories = []

    skip_keywords = {
        "kampanya", "kampanyalar", "gurme", "ferahevler",
        "indirim", "katalog", "iletisim", "hakkimizda",
        "giris", "uye", "sepet", "hesap"
    }

    for a in menu_links:
        href = a.get("href", "")
        name = a.get_text(strip=True)
        if not href or not name:
            continue
        url = urljoin(config.BASE_URL, href)
        if not url.startswith(config.BASE_URL):
            continue
        slug = url.rstrip("/").split("/")[-1].split("?")[0].lower()
        if any(k in slug for k in skip_keywords):
            continue
        if any(k in name.lower() for k in skip_keywords):
            continue
        if url in seen:
            continue
        seen.add(url)
        # Menu nesting: top-level links sit in two <ul>s, their children in three or four.
        level = len([p for p in a.parents if p.name == "ul"]) - 1
        categories.append({
            "level":         level,
            "id":            slug or name,
            "name":          name,
            "url":           url,
            "parent_id":     None,
            "parent_name":   None,
            "product_count": None,
        })

    if not categories:
        raise RuntimeError("Hiçbir kategori bulunamadı.")

    logger.info("Toplam kategori: %d", len(categories))
    return categories
