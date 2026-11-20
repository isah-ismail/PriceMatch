"""Build candidate product pairs between Gratis, Rossmann and Watsons for manual labelling.

Input: daily price CSVs from the class repository (InflationResearchStudy,
InflationItems/Datas/13_Personal_Care/Cosmetics/<Store>/<store>_YYYY-MM-DD.csv).
Output: candidates.csv with similarity scores and parsed attributes; the labels are added by hand.
"""
import csv, re, sys, random, collections
from pathlib import Path
from rapidfuzz import fuzz, process

RAW = Path(sys.argv[1]); OUT = Path(sys.argv[2]); DATE = sys.argv[3]
random.seed(20261120)

UNIT = re.compile(r"(\d+(?:[.,]\d+)?)\s*(ml|gr|g|kg|lt|l|adet|li|lü|lu|cc)\b")
MULTI = re.compile(r"(\d+)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*(ml|g|gr)")

def tr_lower(s):
    return s.replace("İ", "i").replace("I", "ı").lower()

def norm(s):
    s = tr_lower(s)
    s = s.replace("&", " ").replace("'", "").replace("’", "")
    s = re.sub(r"[^\w\s.,/+-]", " ", s)
    s = re.sub(r"\b(\d+)\s*(ml|gr|g)\b", r"\1\2", s)
    s = re.sub(r"\bgr\b", "g", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def size_of(s):
    s = tr_lower(s)
    m = MULTI.search(s)
    if m:
        return f"{m.group(1)}x{m.group(2).replace(',', '.')}{'g' if m.group(3) in ('g','gr') else m.group(3)}"
    m = UNIT.search(s)
    if m:
        u = m.group(2); u = "g" if u == "gr" else ("l" if u == "lt" else u)
        return f"{m.group(1).replace(',', '.')}{u}"
    return ""

def price_of(p):
    p = p.replace("₺", "").replace(".", "").replace(",", ".").strip() if "₺" in p else p
    try: return f"{float(p):.2f}"
    except ValueError: return ""

def load(shop):
    rows = list(csv.DictReader(open(RAW / f"{shop}_{DATE}.csv", encoding="utf-8-sig")))
    seen, out = set(), []
    for r in rows:
        n = r["product_name"].strip()
        if n in seen: continue
        seen.add(n)
        out.append({"shop": shop, "name": n, "norm": norm(n), "size": size_of(n),
                    "brand": norm(n).split(" ")[0], "price": price_of(r["price"]),
                    "subcat": r["sub_category_number"]})
    return out

shops = {s: load(s) for s in ["gratis", "rossmann", "watsons"]}
for s, rows in shops.items():
    print(s, len(rows), "rows,", sum(1 for r in rows if r["size"]), "with size", file=sys.stderr)

def candidates(a, b):
    by_brand = collections.defaultdict(list)
    for j, r in enumerate(b): by_brand[r["brand"]].append(j)
    pairs = []
    for i, ra in enumerate(a):
        idx = by_brand.get(ra["brand"])
        if not idx or len(ra["brand"]) < 3: continue
        choices = {j: b[j]["norm"] for j in idx}
        for _, score, j in process.extract(ra["norm"], choices, scorer=fuzz.token_set_ratio, limit=3, score_cutoff=55):
            pairs.append((i, j, score))
    return pairs

out = []
pid = 0
combos = [("gratis", "watsons"), ("gratis", "rossmann"), ("watsons", "rossmann")]
quota = {("gratis", "watsons"): 100, ("gratis", "rossmann"): 75, ("watsons", "rossmann"): 75}
for sa, sb in combos:
    a, b = shops[sa], shops[sb]
    pairs = candidates(a, b)
    print(sa, sb, "candidates", len(pairs), file=sys.stderr)
    # stratify by score band so the set has clear matches, near-misses and clear non-matches
    bands = {"high": [p for p in pairs if p[2] >= 90], "mid": [p for p in pairs if 72 <= p[2] < 90],
             "low": [p for p in pairs if p[2] < 72]}
    q = quota[(sa, sb)]
    want = {"high": round(q * 0.4), "mid": round(q * 0.4), "low": q - round(q * 0.4) * 2}
    used_a, used_b = set(), set()
    for band, n in want.items():
        pool = bands[band]; random.shuffle(pool)
        # spread over sub-categories: round-robin by subcat
        bysub = collections.defaultdict(list)
        for p in pool: bysub[a[p[0]]["subcat"]].append(p)
        taken = 0
        while taken < n and any(bysub.values()):
            for sub in list(bysub):
                if not bysub[sub]: del bysub[sub]; continue
                i, j, sc = bysub[sub].pop()
                if i in used_a or j in used_b: continue
                used_a.add(i); used_b.add(j)
                pid += 1
                out.append({"pair_id": f"COS-{pid:03d}", "shop_a": sa, "shop_b": sb,
                            "name_a": a[i]["name"], "name_b": b[j]["name"],
                            "price_a": a[i]["price"], "price_b": b[j]["price"],
                            "size_a": a[i]["size"], "size_b": b[j]["size"],
                            "subcat_a": a[i]["subcat"], "subcat_b": b[j]["subcat"],
                            "similarity": sc, "band": band})
                taken += 1
                if taken >= n: break
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print("wrote", len(out), "pairs ->", OUT, file=sys.stderr)
