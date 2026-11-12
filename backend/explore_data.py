"""Data exploration, cleaning, and quality audit script for the Tourism dataset.

Reads the raw dataset 'data/Top Indian Places to Visit.csv' (never modifies it),
cleans and normalizes fields, assigns a stable unique ID, and saves to
'data/cleaned_tourism.csv'.
"""

from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_PATH = PROJECT_ROOT / "data" / "Top Indian Places to Visit.csv"
CLEANED_DATA_PATH = PROJECT_ROOT / "data" / "cleaned_tourism.csv"


def clean_and_audit_dataset():
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(f"Raw dataset not found at {RAW_DATA_PATH}")

    print("=" * 60)
    print("AI TOURISM DATASET QUALITY AUDIT & CLEANING")
    print("=" * 60)

    # 1. Read raw data (keep raw file unchanged)
    raw_df = pd.read_csv(RAW_DATA_PATH)
    raw_rows, raw_cols = raw_df.shape
    print(f"Raw dataset loaded: {raw_rows} rows, {raw_cols} columns")

    df = raw_df.copy()

    # Drop index column if present
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    # Strip column names
    df.columns = df.columns.str.strip()

    # 2. String trimming & normalization
    str_cols = [
        "Zone",
        "State",
        "City",
        "Name",
        "Type",
        "Establishment Year",
        "Airport with 50km Radius",
        "Weekly Off",
        "Significance",
        "DSLR Allowed",
        "Best Time to visit",
    ]

    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].fillna("Not specified").astype(str).str.strip()

    # Normalize state name typo: 'Maharastra' -> 'Maharashtra'
    df["State"] = df["State"].replace({"Maharastra": "Maharashtra"})

    # Normalize Best Time to visit values
    df["Best Time to visit"] = df["Best Time to visit"].replace(
        {"All ": "All", "Anytime": "All"}
    )

    # 3. Numeric conversions & validations
    df["Entrance Fee in INR"] = (
        pd.to_numeric(df["Entrance Fee in INR"], errors="coerce")
        .fillna(0)
        .clip(lower=0)
        .astype(int)
    )

    df["Google review rating"] = (
        pd.to_numeric(df["Google review rating"], errors="coerce")
        .fillna(4.0)
        .clip(lower=1.0, upper=5.0)
        .round(1)
    )

    df["time needed to visit in hrs"] = (
        pd.to_numeric(df["time needed to visit in hrs"], errors="coerce")
        .fillna(2.0)
        .clip(lower=0.5, upper=24.0)
        .round(1)
    )

    df["Number of google review in lakhs"] = (
        pd.to_numeric(df["Number of google review in lakhs"], errors="coerce")
        .fillna(0.1)
        .clip(lower=0.0)
        .round(2)
    )

    # 4. Remove exact duplicates if any
    df = df.drop_duplicates(subset=["Name", "City", "State"])

    # 5. Assign stable unique destination ID (1-indexed)
    df = df.reset_index(drop=True)
    df.insert(0, "id", range(1, len(df) + 1))

    # 6. Save cleaned dataset
    df.to_csv(CLEANED_DATA_PATH, index=False)
    cleaned_rows, cleaned_cols = df.shape
    print(f"Cleaned dataset saved: {cleaned_rows} rows, {cleaned_cols} columns to {CLEANED_DATA_PATH}")

    # 7. Print summary report
    print("\n--- Summary Statistics ---")
    print(f"Total destinations: {len(df)}")
    print(f"Unique States ({df['State'].nunique()}): {', '.join(sorted(df['State'].unique()))}")
    print(f"Unique Attraction Types: {df['Type'].nunique()}")
    print(f"Entrance Fee Range: INR {df['Entrance Fee in INR'].min()} to INR {df['Entrance Fee in INR'].max()} (Median: INR {df['Entrance Fee in INR'].median()})")
    print(f"Rating Range: {df['Google review rating'].min()} to {df['Google review rating'].max()} (Mean: {df['Google review rating'].mean():.2f})")
    print(f"Visit Duration Range: {df['time needed to visit in hrs'].min()} hrs to {df['time needed to visit in hrs'].max()} hrs")
    print("=" * 60)

    return df


if __name__ == "__main__":
    clean_and_audit_dataset()
