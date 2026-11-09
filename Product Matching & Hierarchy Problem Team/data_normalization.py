
from pathlib import Path
import re
import unicodedata

import pandas as pd


ROOT = Path(__file__).resolve().parent

INPUT_FILE = ROOT / "data" / "processed" / "category_12_cleaned.csv"
OUTPUT_FILE = ROOT / "data" / "processed" / "category_12_normalized.csv"


def normalize_text(text):
    """Normalize Turkish and English text for matching."""
    if pd.isna(text):
        return ""

    text = str(text).strip()

    # Turkish-aware lowercase conversion
    text = text.replace("İ", "i").replace("I", "ı").lower()

    # Convert Turkish characters to ASCII
    translation = str.maketrans({
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
    })
    text = text.translate(translation)

    # Remove remaining accents
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        char for char in text
        if not unicodedata.combining(char)
    )

    # Replace punctuation with spaces
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Remove repeated spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


def main():
    df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")

    df["normalized_name"] = df["product_name"].apply(
        normalize_text
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print("Normalization completed!")
    print(f"Total records: {len(df)}")
    print(f"Saved to: {OUTPUT_FILE}")

    print("\nSample normalized records:")

    for _, row in df.head(5).iterrows():
        print(f"\nOriginal:   {row['product_name']}")
        print(f"Normalized: {row['normalized_name']}")


if __name__ == "__main__":
    main()
