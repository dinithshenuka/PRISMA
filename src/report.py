import pandas as pd
import os


def generate_prisma_report(df, initial_counts, duplicates_removed):
    if df.empty:
        print("No data available to generate report.")
        return

    screened_count = len(df)
    included_count = len(df[df["ai_decision"] == "INCLUDE"])
    excluded_count = len(df[df["ai_decision"] == "EXCLUDE"])
    error_count = len(df[df["ai_decision"] == "ERROR"])

    report = f"""
========================================
    PRISMA AUTOMATED SCREENING REPORT
========================================

IDENTIFICATION PHASE:
- Records Identified via APIs: {initial_counts.get('api', 0)}
- Records Identified via Manual: {initial_counts.get('manual', 0)}
- Total Records Identified: {initial_counts.get('total', 0)}
- Duplicates Removed: {duplicates_removed}

SCREENING PHASE:
- Total Records Screened by AI: {screened_count}
- Records Excluded by AI: {excluded_count}
- Records Included by AI: {included_count}
- Errors during Screening: {error_count}

========================================
"""
    print(report)

    # Save the report
    os.makedirs("data/processed", exist_ok=True)
    with open("data/processed/prisma_report.txt", "w") as f:
        f.write(report)

    # Save included papers to CSV
    if included_count > 0:
        included_df = df[df["ai_decision"] == "INCLUDE"]
        included_df.to_csv("data/processed/included_papers.csv", index=False)
        print("Included papers saved to data/processed/included_papers.csv")

    # Save all papers to CSV
    df.to_csv("data/processed/all_screened_papers.csv", index=False)
    print("Full screening dataset saved to data/processed/all_screened_papers.csv")
