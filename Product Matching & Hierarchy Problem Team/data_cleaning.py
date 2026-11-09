
from pathlib import Path
import pandas as pd

# Location of this script
ROOT = Path(__file__).resolve().parent

# Where our raw bank CSV files are stored
RAW_DIR = ROOT / "data" / "raw" / "category_12"

# Where cleaned data will be saved
OUTPUT_DIR = ROOT / "data" / "processed"

BANKS = ["Akbank", "DenizBank", "GarantiBBVA"]


def clean_bank(bank):
    folder = RAW_DIR / bank
    files = sorted(folder.glob("*.csv"))

    if not files:
        print(f"No CSV found for {bank}")
        return None

    # Read the latest available CSV filename
    file_path = files[-1]
    print(f"\nReading {bank}: {file_path.name}")

    df = pd.read_csv(
        file_path,
        dtype=str,
        encoding="utf-8-sig"
    )

    print(f"Original rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")

    # Make sure essential fields exist
    if not {"product_name", "price"}.issubset(df.columns):
        print(f"Missing required fields for {bank}")
        return None

    # Keep only the fields we need for our first prototype
    df = df[["product_name", "price"]].copy()

    # Normalize whitespace
    df["product_name"] = (
        df["product_name"]
        .fillna("")
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

    # Convert numeric price values
    df["price"] = pd.to_numeric(
        df["price"], errors="coerce"
    )

    # Remove missing names and invalid prices
    df = df[
        (df["product_name"] != "")
        & df["price"].notna()
        & (df["price"] >= 0)
    ].copy()

    # Identify the source retailer
    df["retailer"] = bank

    # Internal hierarchy label, not an official CPI code
    df["category"] = "12_Insurance"
    df["subcategory"] = "AnnualCreditCardFees"

    # Remove exact duplicates within the same snapshot
    df = df.drop_duplicates()

    print(f"Cleaned rows: {len(df)}")

    return df


def main():
    datasets = []

    for bank in BANKS:
        cleaned = clean_bank(bank)

        if cleaned is not None:
            datasets.append(cleaned)

    if not datasets:
        print("No valid data found.")
        return

    combined = pd.concat(datasets, ignore_index=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / "category_12_cleaned.csv"

    combined.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nCleaning completed!")
    print(f"Total records: {len(combined)}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()
