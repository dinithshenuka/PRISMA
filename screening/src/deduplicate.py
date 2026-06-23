import pandas as pd


def deduplicate_dataset(df):
    """
    Removes duplicates based on DOI first, then falls back to Title.
    """
    if df.empty:
        return df

    initial_count = len(df)
    print(f"Starting deduplication for {initial_count} records...")

    # Create a copy to avoid chained assignment warnings
    df = df.copy()

    # Clean up DOIs and Titles for better matching
    if "doi" in df.columns:
        df["doi_clean"] = df["doi"].fillna("").astype(str).str.lower().str.strip()
    if "title" in df.columns:
        df["title_clean"] = df["title"].fillna("").astype(str).str.lower().str.strip()

    # Deduplicate by DOI (where DOI is not empty)
    if "doi_clean" in df.columns:
        # Temporarily replace empty strings with NaN so they aren't grouped as duplicates
        df["doi_clean"] = df["doi_clean"].replace("", pd.NA)
        df = df.drop_duplicates(subset=["doi_clean"], keep="first")

    # Deduplicate by Title
    if "title_clean" in df.columns:
        df = df.drop_duplicates(subset=["title_clean"], keep="first")

    # Cleanup temporary columns
    columns_to_drop = [c for c in ["doi_clean", "title_clean"] if c in df.columns]
    df = df.drop(columns=columns_to_drop)

    final_count = len(df)
    duplicates_removed = initial_count - final_count

    print(
        f"Removed {duplicates_removed} duplicates. {final_count} unique records remain."
    )
    return df
