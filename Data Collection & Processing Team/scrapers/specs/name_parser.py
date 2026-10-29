"""
Product specs read from a product *name*, for retailers whose daily data
has nothing but the name (Beymen, and Vatan until its CSV carries a URL).

    parse_name("MacBook Air 13\" M5 Çip 10 Çekirdekli CPU 10 Çekirdekli GPU 24GB Bellek 1TB SSD Gümüş Laptop MDH94TU/A")
    -> {"storage_gb": 1024, "ram_gb": 24, "screen_size_in": 13, "color": "Gümüş",
        "model_code": "MDH94TU/A", "brand": "Apple", "family": "MacBook Air"}

Rules were written against Beymen's names of 2026-10-28; every field is
best-effort and empty when the name does not say it.
"""

import re

import common

# ── storage / RAM ───────────────────────────────────────────────────────────

SIZE_RE = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*(GB|TB)\b", re.IGNORECASE)
# "512 SSD": a disk size written without a unit is in GB.
BARE_SSD_RE = re.compile(r"(?<![\w.])(\d{3,4})\s+SSD\b", re.IGNORECASE)
RAM_AFTER_RE = re.compile(r"^\s*(?:LP)?(?:DDR\d\w*\s+)?(RAM|Bellek|Unified)\b", re.IGNORECASE)
# Graphics memory: "RTX 5060 8GB", "8GB RTX5060", "12GB GeForce", "16GB GDDR7".
GPU_BEFORE_RE = re.compile(r"(RTX|GTX|GeForce|Arc|Blackwell|Radeon)[\w ]{0,12}$", re.IGNORECASE)
GPU_AFTER_RE = re.compile(r"^\s*(GDDR|GeForce|RTX|GTX|NVIDIA|Radeon)", re.IGNORECASE)


def _gb(value, unit):
    gb = float(value.replace(",", ".")) * (1024 if unit.upper() == "TB" else 1)
    return int(gb) if gb.is_integer() else gb


def storage_and_ram(name):
    """(storage_gb, ram_gb). A size followed by RAM/Bellek is RAM; graphics memory is skipped.
    Of the unmarked sizes the largest is storage and, when there are two, the smaller is RAM."""
    ram, unmarked = None, []
    for m in SIZE_RE.finditer(name):
        before, after = name[:m.start()], name[m.end():]
        if GPU_BEFORE_RE.search(before) or GPU_AFTER_RE.match(after):
            continue
        size = _gb(m.group(1), m.group(2))
        if RAM_AFTER_RE.match(after):
            ram = ram or size
        else:
            unmarked.append(size)
    unmarked += [int(m.group(1)) for m in BARE_SSD_RE.finditer(name)]
    if not unmarked:
        return None, ram
    storage = max(unmarked)
    smaller = [s for s in unmarked if s < storage and s <= 128]
    if ram is None and smaller:
        ram = smaller[0]
    return storage, ram


# ── colour ──────────────────────────────────────────────────────────────────

COLORS = [
    # multi-word names first; the alternation tries longer names before their parts
    "Kozmik Turuncu", "Uzay Grisi", "Uzay Siyahı", "Yıldız Işığı", "Gece Yarısı", "Gök Mavisi",
    "Sis Mavisi", "Deniz Mavisi", "Buz Mavisi", "Abis Mavisi", "Kobalt Mor", "Ada Çayı", "Adaçayı",
    "Pamuk Beyazı", "Su Yeşili", "Açık Mavi", "Koyu Mavi", "Derin Mavi", "Açık Mor", "Koyu Gri",
    "Rose Gold", "Natürel Titanyum", "Çöl Titanyum", "Siyah Titanyum", "Beyaz Titanyum",
    "Titanyum Gri", "Titanyum Siyah", "Titanyum Gümüş", "Titanyum Mavi", "Grafit Gri",
    "Laciverttaş", "Lavanta", "Abis", "Grafit", "Antrasit", "Titanyum",
    "Siyah", "Beyaz", "Gümüş", "Gri", "Mavi", "Lacivert", "Kırmızı", "Yeşil", "Pembe", "Mor",
    "Lila", "Sarı", "Turuncu", "Altın", "Bej", "Krem", "Kahverengi", "Bordo", "Mint", "Şeffaf",
    "Black", "White", "Silver", "Blue", "Green", "Pink", "Purple", "Red", "Grey", "Gray", "Gold",
    "Midnight", "Starlight",
]
COLOR_RE = re.compile(r"(?<!\w)(" + "|".join(sorted(map(re.escape, COLORS), key=len, reverse=True)) + r")(?!\w)",
                      re.IGNORECASE)


def color(name):
    match = COLOR_RE.search(name)
    return match.group(1) if match else ""


# ── model code ──────────────────────────────────────────────────────────────

APPLE_CODE_RE = re.compile(r"\b[A-Z0-9]{4,6}(?:TU|ZM|LL|ZE)/A\b")
SAMSUNG_CODE_RE = re.compile(r"\b(?:SM|EF|EP|ET|EB|GP)-[A-Z0-9]{4,}\b")
CODE_TOKEN_RE = re.compile(r"^(?=.*\d)(?=.*[A-Z])[A-Z0-9][A-Z0-9\-/]{4,}$")
NOT_A_CODE_RE = re.compile(
    r"^(RTX|GTX|RX|DDR|LPDDR|GDDR|USB|HDMI|WIFI|PS\d|W\d+$|S\d\d$|M\d)"
    r"|^\d+(GB|TB|MB|MHZ|GHZ|HZ|W|MAH|MP|MM|CM|K|FPS|NIT|NITS)$")


def model_code(name):
    """Apple / Samsung part numbers first, then a code-like last token, then a code-like first token."""
    for pattern in (APPLE_CODE_RE, SAMSUNG_CODE_RE):
        match = pattern.search(name)
        if match:
            return match.group(0)
    tokens = [t.strip(".,;:()[]™®") for t in name.split()]
    codes = [t for t in tokens if CODE_TOKEN_RE.match(t) and not NOT_A_CODE_RE.match(t)]
    if not codes:
        return ""
    if tokens and codes[-1] == tokens[-1]:
        return codes[-1]
    if codes[0] == tokens[0]:
        return codes[0]
    return codes[-1]


# ── brand / family ──────────────────────────────────────────────────────────

# Product lines that name their maker; checked as whole words, case-insensitive.
LINE_BRANDS = {
    "Apple": ["iPhone", "iPad", "MacBook", "iMac", "Mac mini", "Mac Studio", "AirPods", "Apple Watch",
              "Apple", "MagSafe Şarj Aleti", "Vision Pro"],
    "Samsung": ["Galaxy", "Tizen", "Neo QLED", "The Frame", "Odyssey", "Samsung"],
    "Lenovo": ["ThinkPad", "ThinkBook", "IdeaPad", "Legion", "LOQ", "Yoga", "Lenovo"],
    "Asus": ["ROG", "TUF", "Zenbook", "Vivobook", "ProArt", "Asus"],
    "HP": ["OMEN", "Victus", "Pavilion", "EliteBook", "ProBook", "OmniBook", "HP"],
    "Dell": ["XPS", "Inspiron", "Latitude", "Alienware", "Dell"],
    "Huawei": ["Pura", "MatePad", "MateBook", "FreeBuds", "Huawei"],
    "Xiaomi": ["Redmi", "POCO", "Xiaomi"],
    "LG": ["webOS", "StanbyME", "LG"],
    "Sony": ["PlayStation", "PS5", "Sony"],
    "Fujifilm": ["Instax", "Fujifilm"],
    "DJI": ["Osmo", "DJI"],
    "Google": ["Pixel"],
    "Microsoft": ["Surface", "Xbox"],
    "Dyson": ["Dyson"], "JBL": ["JBL"], "Marshall": ["Marshall"], "Bose": ["Bose"],
    "Bang & Olufsen": ["Bang & Olufsen", "Beosound", "Beoplay"], "Beats": ["Beats"],
    "Garmin": ["Garmin"], "Philips": ["Philips"], "Canon": ["Canon"], "Nikon": ["Nikon"],
    "GoPro": ["GoPro"], "Nintendo": ["Nintendo"], "Logitech": ["Logitech"], "Anker": ["Anker"],
    "Belkin": ["Belkin"], "Baseus": ["Baseus"], "Native Union": ["Native Union"], "Smeg": ["Smeg"],
    "KitchenAid": ["KitchenAid"], "De'Longhi": ["De'Longhi", "Delonghi"], "Nespresso": ["Nespresso"],
    "Bosch": ["Bosch"], "Siemens": ["Siemens"], "Tefal": ["Tefal"], "Braun": ["Braun"],
    "Remington": ["Remington"], "ghd": ["ghd"], "Rowenta": ["Rowenta"], "Acer": ["Acer"],
    "MSI": ["Prestige", "Katana", "Cyborg", "Raider", "Crosshair", "MSI"],
}
BRAND_RES = [(brand, re.compile(r"(?<!\w)(" + "|".join(map(re.escape, words)) + r")(?!\w)", re.IGNORECASE))
             for brand, words in LINE_BRANDS.items()]
# A maker's own name opening the product name: "Belkin ...", "Apple MagSafe ...".
MAKER_RES = [(brand, re.compile(r"^" + re.escape(brand) + r"(?!\w)", re.IGNORECASE)) for brand in LINE_BRANDS]


def brand(name, code="", device=True):
    """Brand from the part number, else from the name. For a device the earliest product line
    or maker named wins. For an accessory a product line names what it fits ("iPhone 17 Kılıfı"),
    so only a maker's name at the start counts, and nothing when the name says "Uyumlu"."""
    if code.endswith("/A"):
        return "Apple"
    if code.startswith(("SM-", "EF-", "EP-", "ET-", "EB-", "GP-")):
        return "Samsung"
    if not device:
        if "uyumlu" in name.lower():
            return ""
        return next((b for b, rx in MAKER_RES if rx.match(name)), "")
    hits = [(m.start(), b) for b, rx in BRAND_RES for m in [rx.search(name)] if m]
    return min(hits)[1] if hits else ""


FAMILY_END_RE = re.compile(r"\s(\d+(?:[.,]\d+)?\s*(?:GB|TB)\b|\d+(?:[.,]\d+)?\s*(?:\"|”|''|inç)|Wi-?Fi|Akıllı|Laptop|Tablet)",
                           re.IGNORECASE)


def family(name):
    """'iPhone 17 Pro 256GB ...' -> 'iPhone 17 Pro': the text before the first spec."""
    match = FAMILY_END_RE.search(name)
    return name[:match.start()].strip() if match else ""


# ── all together ────────────────────────────────────────────────────────────

def parse_name(name, device=True):
    """Specs found in a product name. With device=False (cases, straps, ...) sizes in the
    name describe what the accessory fits, so storage, RAM, screen size and family stay empty."""
    name = " ".join((name or "").split())
    code = model_code(name)
    specs = {"model_code": code, "brand": brand(name, code, device), "color": color(name),
             "storage_gb": None, "ram_gb": None, "screen_size_in": None, "family": ""}
    if device:
        specs["storage_gb"], specs["ram_gb"] = storage_and_ram(name)
        specs["screen_size_in"] = common.screen_size_in(name)
        specs["family"] = family(name)
    return specs
