"""Build 250 labelled dormitory-room comparison pairs from three universities.

Input : the Dormitories folder of the class repository
        (InflationItems/Datas/11_Restaurants/Accommodations/Dormitories/<University>/<University>_YYYY-MM-DD.csv)
Output: dorm_pairs_manual.csv (next to this script unless a path is given)

Usage : python build_dorm_pairs.py [<Dormitories folder>] [<output csv>]

The source files are only read, never modified.

How labels are decided
----------------------
Every source row was read by hand and its room specification written into ROOM_SPECS
below (Bilkent, Ozyegin) or parsed from Ankara's very regular room names (ankara_spec).
The label of a pair is then derived from those hand-written specs:

  same        same occupancy, same room class, and no explicit conflict in bed type
              (bunk vs normal bed) or kitchen (kitchenette vs none)
  comparable  same occupancy, but a different room class (standard / en-suite / suite /
              studio / partitioned room) or an explicit bed/kitchen conflict
              -> like "same phone, different colour"
  different   different number of people in the room (a single room is not a substitute
              for a four-person room)

The manual_reason column is left empty by this script; reasons are written by hand.

The dorm building, campus, city and gender of the dorm are not part of the product
(like the store is not part of a phone); they are visible in the names.
"""
import csv
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SRC = HERE.parent / "DataScraping/InflationResearchStudy/InflationItems/Datas/11_Restaurants/Accommodations/Dormitories"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "dorm_pairs_manual.csv"

SHOPS = {"Bilkent": "Bilkent Üniversitesi",
         "Ozyegin": "Özyeğin Üniversitesi",
         "Ankara": "Ankara Üniversitesi"}
# Number of pairs per store pair (sums to 250).
QUOTA = {("Bilkent", "Ozyegin"): 84, ("Bilkent", "Ankara"): 83, ("Ozyegin", "Ankara"): 83}
# Target label mix inside each store pair (filled from the next label if one runs short).
MIX = {"same": 0.32, "comparable": 0.30, "different": 0.38}
random.seed(20261120)

# ---------------------------------------------------------------------------
# Hand-written room specifications.
# occ: people per room | cls: standard / ensuite / suite / studio / partitioned
# bed: bunk / bed / None (not stated) | kitchen: yes / no / None (not stated)
# explicit: True when the source name states the room class itself
# ---------------------------------------------------------------------------
def spec(occ, cls, bed=None, kitchen=None, explicit=True, note=""):
    return dict(occ=occ, cls=cls, bed=bed, kitchen=kitchen, explicit=explicit, note=note)

ROOM_SPECS = {
    "Bilkent": {
        "4S": spec(4, "standard", "bunk", note="4-person standard, bunk beds"),
        "3S": spec(3, "standard", "bed", note="3-person standard, normal beds"),
        "2R": spec(2, "standard", "bunk", note="double standard, bunk bed"),
        "2K": spec(2, "standard", "bed", note="double standard, normal beds"),
        "2B": spec(2, "ensuite", "bed", "no", note="double with private bathroom"),
        "1S": spec(1, "standard", None, note="single standard"),
        "1OO": spec(1, "suite", "bed", "yes", note="single with private bath, kitchen shared with neighbour room"),
        "STE1": spec(1, "suite", "bed", "no", note="single suite with private bath and sitting area"),
        "D4S": spec(4, "standard", "bunk", note="4-person standard, bunk beds"),
        "D3S": spec(3, "standard", "bed", note="3-person standard, normal beds"),
        "D2R": spec(2, "standard", "bunk", note="double standard, bunk bed"),
        "D2K": spec(2, "standard", "bed", note="double standard, normal beds"),
        "DSTE2": spec(2, "suite", None, "yes", note="two-room suite with private bath and kitchen"),
        "D1S": spec(1, "standard", None, note="single standard"),
        "D1B": spec(1, "ensuite", "bed", "no", note="single with private bathroom"),
    },
    "Ozyegin": {
        "STÜDYO ODA TEK KİŞİLİK STANDART ODA": spec(1, "studio", note="single studio room"),
        "STÜDYO ODA TEK KİŞİLİK, MİNİ MUTFAKLI ODA": spec(1, "studio", kitchen="yes", note="single studio with kitchenette"),
        "STÜDYO ODA TEK KİŞİLİK MİNİ MUTFAK TEFRİŞATLI ODA": spec(1, "studio", kitchen="yes", note="single studio with kitchenette"),
        "2 KİŞİLİK SUİT ÖZEL ODA İKİ KİŞİLİK ORTAK KULLANIM ALANLI BİREYSEL ODA": spec(2, "suite", note="2-person suite, individual rooms + shared living area"),
        "2 KİŞİLİK SUİT ÖZEL ODA İKİ KİŞİLİK, MİNİ MUTFAKLI VE ORTAK KULLANIM ALANLI BİREYSEL ODA": spec(2, "suite", kitchen="yes", note="2-person suite with kitchenette"),
        "2 KİŞİLİK SUİT ÖZEL ODA İKİ KİŞİLİK MİNİ MUTFAK TEFRİŞATLI VE ORTAK KULLANIM ALANLI BİREYSEL ODA": spec(2, "suite", kitchen="yes", note="2-person suite with kitchenette"),
        "3 KİŞİLİK ODA ÜÇ KİŞİLİK STANDART ODA": spec(3, "standard", "bed", note="3-person standard"),
        "3 KİŞİLİK BÖLMELİ ODA ÜÇ KİŞİLİK BÖLMELİ ODA": spec(3, "partitioned", note="3-person partitioned room"),
        "3 KİŞİLİK SUİT ÖZEL ODA ÜÇ KİŞİLİK, MİNİ MUTFAKLI VE ORTAK KULLANIM ALANLI BİREYSEL ODA": spec(3, "suite", kitchen="yes", note="3-person suite with kitchenette"),
        "3 KİŞİLİK SÜİT ÖZEL ODA ÜÇ KİŞİLİK, MİNİ MUTFAKLI VE ORTAK KULLANIM ALANLI BİREYSEL ODA": spec(3, "suite", kitchen="yes", note="3-person suite with kitchenette"),
        "3 KİŞİLİK SUİT ÖZEL ODA ÜÇ KİŞİLİK MİNİ MUTFAK TEFRİŞATLI VE ORTAK KULLANIM ALANLI BİREYSEL ODA": spec(3, "suite", kitchen="yes", note="3-person suite with kitchenette"),
        # Ozyegin lists "standart" and "ranzalı" 4-person rooms separately, so standard = normal beds.
        "4 KİŞİLİK ODA DÖRT KİŞİLİK STANDART ODA": spec(4, "standard", "bed", note="4-person standard, normal beds"),
        "4 KİŞİLİK RANZALI ODA DÖRT KİŞİLİK RANZALI ODA": spec(4, "standard", "bunk", note="4-person standard, bunk beds"),
    },
}

OCC_WORDS = {"tek": 1, "iki": 2, "çift": 2, "üç": 3, "dört": 4, "beş": 5}


def tr_lower(s):
    return s.replace("İ", "i").replace("I", "ı").lower()


def ankara_spec(room):
    """Ankara room names follow '<Word> Kişilik [Standart|Süit] Oda Aylık (Kişi Başı)'."""
    low = tr_lower(room)
    occ = OCC_WORDS[low.split()[0]]
    if "süit" in low:
        return spec(occ, "suite", note=f"{occ}-person suite")
    explicit = "standart" in low
    return spec(occ, "standard", explicit=explicit,
                note=f"{occ}-person standard" + ("" if explicit else " (class not stated, assumed standard)"))


def bilkent_code(room):
    # "Çift Kişilik Odalar 2K Karyolalı, standart" -> "2K"
    m = re.search(r"Odalar\s+(\S+)", room)
    return m.group(1)


def room_spec(shop, room):
    if shop == "Ankara":
        return ankara_spec(room)
    key = bilkent_code(room) if shop == "Bilkent" else room
    return ROOM_SPECS[shop][key]  # KeyError = new room type that still needs a hand-written spec


def latest_csv(folder):
    files = sorted(folder.glob("*_20??-??-??.csv"))
    if not files:
        raise SystemExit(f"No dated CSV in {folder}")
    return files[-1]


def load(shop):
    path = latest_csv(SRC / SHOPS[shop])
    rows, seen = [], set()
    with open(path, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            name = r["product_name"].strip()
            if name in seen:
                continue
            seen.add(name)
            parts = [p.strip() for p in name.split("|")]
            rows.append(dict(shop=shop, name=name, dorm=parts[1], room=parts[2], basis=parts[3],
                             price=f"{float(r['price']):.2f}", sub=r["sub_category_number"],
                             date=path.stem.rsplit("_", 1)[1], spec=room_spec(shop, parts[2])))
    return rows


def label(a, b):
    sa, sb = a["spec"], b["spec"]
    implicit = not (sa["explicit"] and sb["explicit"])
    if sa["occ"] != sb["occ"]:
        return "different", "high"
    if sa["cls"] != sb["cls"]:
        # Ankara does not say what its "süit" rooms include, so en-suite vs suite stays uncertain.
        vague = {sa["cls"], sb["cls"]} == {"ensuite", "suite"} and "Ankara" in (a["shop"], b["shop"])
        return "comparable", "medium" if implicit or vague else "high"
    conflict = unknown = False
    for attr in ("bed", "kitchen"):
        if sa[attr] and sb[attr] and sa[attr] != sb[attr]:
            conflict = True
        elif (sa[attr] is None) != (sb[attr] is None) and (attr == "bed" or sa["cls"] in ("suite", "studio")):
            unknown = True
    if conflict:
        return "comparable", "high"
    return "same", "medium" if implicit or unknown else "high"


def pick(pairs, n):
    """Random pick that prefers pairs whose room texts were not used yet (more variety)."""
    random.shuffle(pairs)
    pairs.sort(key=lambda p: (p[0]["room"], p[1]["room"]) in USED)
    chosen = pairs[:n]
    for a, b, *_ in chosen:
        USED.add((a["room"], b["room"]))
    return chosen


USED = set()


def main():
    if OUT.exists():
        sys.exit(f"{OUT} already exists and may hold hand-written reasons; pass a different output path.")
    data = {s: load(s) for s in SHOPS}
    for s, rows in data.items():
        print(f"{s}: {len(rows)} rows ({rows[0]['date']})", file=sys.stderr)

    out = []
    for (sa, sb), quota in QUOTA.items():
        buckets = {"same": [], "comparable": [], "different": []}
        for a in data[sa]:
            for b in data[sb]:
                lab, conf = label(a, b)
                buckets[lab].append((a, b, lab, conf))
        print(f"{sa}-{sb}: " + ", ".join(f"{k}={len(v)}" for k, v in buckets.items()), file=sys.stderr)
        # Hard negatives first: 'different' pairs whose occupancy differs by one person.
        diff = buckets["different"]
        hard = [p for p in diff if abs(p[0]["spec"]["occ"] - p[1]["spec"]["occ"]) == 1]
        easy = [p for p in diff if p not in hard]
        want = {k: round(quota * v) for k, v in MIX.items()}
        want["different"] = quota - want["same"] - want["comparable"]
        chosen = []
        for lab in ("same", "comparable"):
            got = pick(buckets[lab], want[lab])
            want["different"] += want[lab] - len(got)  # shortfall goes to 'different'
            chosen += got
        n_hard = min(len(hard), round(want["different"] * 0.6))
        chosen += pick(hard, n_hard) + pick(easy, want["different"] - n_hard)
        random.shuffle(chosen)
        out += chosen

    cols = ["pair_id", "shop_a", "name_a", "price_a", "shop_b", "name_b", "price_b",
            "manual_label", "confidence", "manual_reason",
            "occupancy_a", "occupancy_b", "room_type_a", "room_type_b",
            "tuik_sub_a", "tuik_sub_b", "price_basis_a", "price_basis_b"]
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for i, (a, b, lab, conf) in enumerate(out, 1):
            w.writerow([f"DORM-{i:03d}", SHOPS[a["shop"]], a["name"], a["price"], SHOPS[b["shop"]], b["name"], b["price"],
                        lab, conf, "", a["spec"]["occ"], b["spec"]["occ"], a["spec"]["cls"], b["spec"]["cls"],
                        a["sub"], b["sub"], a["basis"], b["basis"]])
    print(f"wrote {len(out)} pairs -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
