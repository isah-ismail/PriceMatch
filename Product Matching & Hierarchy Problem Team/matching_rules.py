"""Shared matching rules for Beymen and Pozitif iPhones."""

import re
import unicodedata
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz


ROOT = Path(__file__).resolve().parent
DATA_TEAM = ROOT.parent / "Data Collection & Processing Team" / "data"
RESULTS = ROOT / "data" / "results"

SHOPS = ("beymen", "pozitif")
VERSION = "iphone-week3-v2"
THRESHOLD = 0.80

REQUIRED_SPEC_COLUMNS = {
    "listing_id",
    "name",
    "brand",
    "category",
    "model_code",
    "storage_gb",
    "color",
    "condition",
    "is_bundle",
    "url",
}

# Add colour aliases only after checking the original listings.
COLOUR_ALIASES = {}

IPHONE_PATTERN = re.compile(
    r"\biphone\s*"
    r"(?P<model>"
    r"\d{1,2}(?:\s*e)?"
    r"(?:\s+pro\s+max|\s+pro|\s+plus|\s+mini)?"
    r"|air|duo"
    r")\b"
)


def text(value):
    """Convert a scalar value to text, preserving missing values as blank."""
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def normalize(value):
    """Normalize case, Turkish characters and whitespace."""
    value = text(value)
    value = value.replace("İ", "i").replace("ı", "i").casefold()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )
    return " ".join(value.split())


def clean_name(value):
    """Normalize a name and remove common phone-description filler."""
    value = normalize(value)
    value = re.sub(
        r"\b(?:akilli|akili)\s+cep\s+telefonu\b",
        " ",
        value,
    )
    value = re.sub(r"(\d+)\s+(gb|tb)\b", r"\1\2", value)
    return " ".join(value.split())


def extract_model(value):
    """Extract an iPhone model from supplied text."""
    match = IPHONE_PATTERN.search(normalize(value))
    if not match:
        return ""

    model = re.sub(
        r"(\d+)\s+e\b",
        r"\1e",
        match.group("model"),
    )
    return "iphone " + model


def normalize_storage(value):
    """
    Normalize storage to a GB label.

    Project convention: 1 TB = 1024 GB.
    This should agree with the cleaning team's data dictionary.
    """
    value = normalize(value).replace(",", ".")
    match = re.fullmatch(
        r"(\d+(?:\.\d+)?)\s*(gb|tb)?",
        value,
    )

    if not match:
        return ""

    amount = float(match.group(1))

    if match.group(2) == "tb":
        amount *= 1024

    if amount <= 0 or not amount.is_integer():
        return ""

    return str(int(amount))


def normalize_colour(value):
    value = normalize(value).replace(" ", "")
    return COLOUR_ALIASES.get(value, value)


def normalize_condition(value):
    value = normalize(value)

    if value in {"new", "yeni", "sifir"}:
        return "new"

    return value


def parse_bool(value):
    value = normalize(value)

    if value in {"true", "1", "yes", "evet"}:
        return True

    if value in {"false", "0", "no", "hayir"}:
        return False

    return None


def read_csv(path):
    """Read identifiers as strings and preserve empty cells."""
    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )


def load_specs(shop):
    """Load actual iPhone devices, excluding accessories by category."""
    if shop not in SHOPS:
        raise ValueError(f"Unsupported shop: {shop}")

    path = DATA_TEAM / "clean" / f"{shop}_specs.csv"

    if not path.exists():
        raise FileNotFoundError(f"Missing cleaned specs: {path}")

    source = read_csv(path)

    missing = REQUIRED_SPEC_COLUMNS - set(source.columns)
    if missing:
        raise ValueError(
            f"{path.name}: missing columns {sorted(missing)}"
        )

    categories = source["category"].map(normalize)
    has_iphone_model = source["name"].map(extract_model).ne("")

    # These rules match the categories in your cleaned source files.
    if shop == "beymen":
        phone_category = categories.eq("cep telefonu")
    else:
        phone_category = (
            categories.eq("iphone")
            | categories.str.startswith("iphone > ")
        )

    source = source.loc[
        phone_category & has_iphone_model
    ].copy()

    if source.empty:
        raise ValueError(
            f"{path.name}: no iPhone devices found in the expected "
            "phone categories. Check the source data dictionary."
        )

    source["listing_id"] = source["listing_id"].map(text)

    if source["listing_id"].eq("").any():
        raise ValueError(f"{path.name}: blank listing IDs")

    duplicates = source["listing_id"].duplicated(keep=False)
    if duplicates.any():
        examples = source.loc[
            duplicates, "listing_id"
        ].head(5).tolist()

        raise ValueError(
            f"{path.name}: duplicate listing IDs, for example {examples}. "
            "Resolve duplicate records upstream."
        )

    records = []

    for row in source.to_dict("records"):
        name_model = extract_model(row["name"])
        family_model = extract_model(row.get("family", ""))

        records.append({
            "shop": shop,
            "listing_id": row["listing_id"],
            "name": row["name"],
            "brand": normalize(row["brand"]),
            "category": row["category"],
            "model": family_model or name_model,
            "model_code": text(row["model_code"]).upper(),
            "storage_gb": normalize_storage(row["storage_gb"]),
            "colour": normalize_colour(row["color"]),
            "condition": normalize_condition(row["condition"]),
            "is_bundle": parse_bool(row["is_bundle"]),
            "url": row["url"],
            "source_conflict": bool(
                family_model and family_model != name_model
            ),
        })

    return pd.DataFrame(records)


def iphone_scope(row):
    """Check whether a listing is eligible for this comparison."""
    if row.get("source_conflict"):
        return False, "Title and family disagree about model"

    if row.get("brand") != "apple":
        return False, "Apple brand missing or inconsistent"

    if row.get("condition") != "new":
        return False, "Condition is missing or outside new-product scope"

    if row.get("is_bundle") is not False:
        return False, "Bundle status is true or unverified"

    return True, ""


def attribute_decision(a, b):
    """
    Return (decision, reason).

    same:
        Sufficient consistent evidence for the exact variant.
    different:
        A known model, storage or colour conflict.
    review:
        Missing, ambiguous or contradictory evidence.
    """
    for row in (a, b):
        valid, reason = iphone_scope(row)
        if not valid:
            return "review", reason

    code_a = a["model_code"]
    code_b = b["model_code"]
    same_code = bool(code_a and code_b and code_a == code_b)

    fields = ("model", "storage_gb", "colour")

    conflicts = [
        field
        for field in fields
        if a[field] and b[field] and a[field] != b[field]
    ]

    if conflicts:
        reason = "Attribute conflict: " + ", ".join(conflicts)

        if same_code:
            return "review", "Same code but " + reason.lower()

        return "different", reason

    if same_code:
        return "same", "Same manufacturer code; no known conflict"

    if code_a and code_b:
        return (
            "review",
            "Different manufacturer codes need verification",
        )

    missing = [
        field
        for field in fields
        if not a[field] or not b[field]
    ]

    if missing:
        return "review", "Missing attributes: " + ", ".join(missing)

    return "same", "Same model, storage and colour"


def hybrid_decision(a, b, threshold=THRESHOLD):
    """
    Apply attribute rules, then a fuzzy-name confidence check.

    Similarity never overrides an attribute conflict or missing evidence.
    An agreeing manufacturer code bypasses the fuzzy-name check.
    """
    decision, reason = attribute_decision(a, b)

    if decision != "same":
        return decision, reason

    if a["model_code"] and a["model_code"] == b["model_code"]:
        return decision, reason

    similarity = fuzz.token_sort_ratio(
        clean_name(a["name"]),
        clean_name(b["name"]),
    ) / 100

    if similarity >= threshold:
        return (
            "same",
            f"Attributes agree; name score={similarity:.3f}",
        )

    return (
        "review",
        f"Attributes agree but name score={similarity:.3f}",
    )


def candidate_pairs(left, right, max_pairs=100_000):
    """
    Generate cross-shop candidates sharing a model or manufacturer code.

    Shared-code candidates are retained even if their models disagree,
    so contradictory records can be flagged.
    """
    by_model = {}
    by_code = {}

    for index, row in enumerate(right):
        if row["model"]:
            by_model.setdefault(row["model"], set()).add(index)

        if row["model_code"]:
            by_code.setdefault(row["model_code"], set()).add(index)

    count = 0

    for a in left:
        indices = set(by_model.get(a["model"], set()))

        if a["model_code"]:
            indices.update(
                by_code.get(a["model_code"], set())
            )

        for index in sorted(indices):
            count += 1

            if count > max_pairs:
                raise ValueError(
                    "Candidate limit exceeded. Narrow the sample or "
                    "implement batch processing before expanding."
                )

            yield a, right[index]


def product_identity(row):
    """Return an identity fingerprint used to check dataset overlap."""
    if row["model_code"]:
        return (
            "code",
            row["brand"],
            row["model_code"],
        )

    return (
        "attributes",
        row["brand"],
        row["model"],
        row["storage_gb"],
        row["colour"],
    )