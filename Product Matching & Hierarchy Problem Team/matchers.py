"""
The matching algorithms compared in the benchmark.

Every algorithm receives only the two product names and returns a score
between 0 and 1. A pair is predicted to be the same product when its score
reaches the algorithm's threshold. Barcodes and the catalog's model column are
never used here, because they were used to choose the labeled pairs.

    exact_score       1 if the normalized names are identical, else 0
    fuzzy_score       RapidFuzz token-sort similarity of the normalized names
    TfidfMatcher      cosine similarity of character n-gram TF-IDF vectors
    attribute_score   fuzzy_score, set to 0 when a size, pack count, storage,
                      model code or condition found in the two names disagrees

pair_features() turns a pair into the numbers the supervised model learns from.
"""

import re

from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer

from data_normalization import normalize_text

NUMBER = r"(\d+(?:[.,]\d+)?)"
MEASURES = {
    "weight_g": (rf"{NUMBER}\s*(kg|gr|g)\b", {"kg": 1000, "gr": 1, "g": 1}),
    "volume_ml": (rf"{NUMBER}\s*(ml|cl|lt|l)\b", {"ml": 1, "cl": 10, "lt": 1000, "l": 1000}),
    "storage_gb": (rf"{NUMBER}\s*(tb|gb)\b", {"tb": 1024, "gb": 1}),
    "pack_count": (rf"{NUMBER}\s*'?\s*(l[iıuü]|adet|x)\b", {"": 1}),
    "screen_in": (rf"{NUMBER}\s*(\"|”|''|inç|inc|inch)", {"": 1}),
}
MODEL_CODE = re.compile(r"[A-Z0-9]+(?:[-/][A-Z0-9]+)*(?![a-zçğıöşü])")
QUANTITY_TOKEN = re.compile(r"^\d+([.,]\d+)?[A-Z]{0,4}$")
CONDITION_WORDS = ("teşhir", "outlet", "ikinci el", "yenilenmiş")
ATTRIBUTES = list(MEASURES) + ["model_code", "condition"]


def turkish_lower(text):
    return str(text).replace("İ", "i").replace("I", "ı").lower()


def extract_attributes(name):
    """Reads sizes, pack count, storage, model codes and condition out of a product name."""
    lowered = turkish_lower(name)
    found = {}
    for attribute, (pattern, factors) in MEASURES.items():
        values = set()
        for number, unit in re.findall(pattern, lowered):
            values.add(round(float(number.replace(",", ".")) * factors.get(unit, 1), 3))
        found[attribute] = values
    found["model_code"] = {
        code for code in MODEL_CODE.findall(str(name))
        if len(code) >= 6 and any(c.isdigit() for c in code)
        and any(c.isalpha() for c in code) and not QUANTITY_TOKEN.match(code)
    }
    found["condition"] = {word for word in CONDITION_WORDS if word in lowered} or {"new"}
    return found


def attribute_agreement(name_a, name_b):
    """Per attribute: 1 both names give it and agree, -1 both give it and disagree, 0 at least one is silent."""
    a, b = extract_attributes(name_a), extract_attributes(name_b)
    agreement = {}
    for attribute in ATTRIBUTES:
        if not a[attribute] or not b[attribute]:
            agreement[attribute] = 0
        elif attribute == "condition":
            agreement[attribute] = 1 if a[attribute] == b[attribute] else -1
        else:
            agreement[attribute] = 1 if a[attribute] & b[attribute] else -1
    return agreement


def exact_score(name_a, name_b):
    return float(normalize_text(name_a) == normalize_text(name_b))


def fuzzy_score(name_a, name_b):
    return fuzz.token_sort_ratio(normalize_text(name_a), normalize_text(name_b)) / 100


def attribute_score(name_a, name_b):
    if -1 in attribute_agreement(name_a, name_b).values():
        return 0.0
    return fuzzy_score(name_a, name_b)


class TfidfMatcher:
    """Weights rare character sequences more than common ones, then compares the two names' vectors."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)

    def fit(self, names):
        self.vectorizer.fit([normalize_text(n) for n in names])
        return self

    def score(self, name_a, name_b):
        vectors = self.vectorizer.transform([normalize_text(name_a), normalize_text(name_b)])
        return float(vectors[0].multiply(vectors[1]).sum())


def pair_features(name_a, name_b, tfidf):
    """The inputs of the supervised model: text similarities plus attribute agreement."""
    norm_a, norm_b = normalize_text(name_a), normalize_text(name_b)
    tokens_a, tokens_b = set(norm_a.split()), set(norm_b.split())
    features = {
        "exact": float(norm_a == norm_b),
        "token_sort": fuzz.token_sort_ratio(norm_a, norm_b) / 100,
        "token_set": fuzz.token_set_ratio(norm_a, norm_b) / 100,
        "partial": fuzz.partial_ratio(norm_a, norm_b) / 100,
        "tfidf_cosine": tfidf.score(name_a, name_b),
        "token_jaccard": len(tokens_a & tokens_b) / max(len(tokens_a | tokens_b), 1),
        "same_first_token": float(norm_a.split()[:1] == norm_b.split()[:1]),
        "length_ratio": min(len(norm_a), len(norm_b)) / max(len(norm_a), len(norm_b), 1),
    }
    for attribute, value in attribute_agreement(name_a, name_b).items():
        features[f"{attribute}_agreement"] = value
    return features
