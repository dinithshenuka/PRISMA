import os
import graphviz


def generate_prisma_report(df, initial_counts, duplicates_removed):
    if df.empty:
        print("No data available to generate report.")
        return

    screened_count = len(df)
    included_count = len(df[df["ai_decision"] == "INCLUDE"])
    excluded_count = len(df[df["ai_decision"] == "EXCLUDE"])
    notsure_count = len(df[df["ai_decision"] == "NOT SURE"])
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
- Records Not Sure by AI: {notsure_count}
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

    if notsure_count > 0:
        notsure_df = df[df["ai_decision"] == "NOT SURE"]
        notsure_df.to_csv("data/processed/notsure_papers.csv", index=False)
        print("Not Sure papers saved to data/processed/notsure_papers.csv")

    # Save all papers to CSV
    df.to_csv("data/processed/all_screened_papers.csv", index=False)
    print("Full screening dataset saved to data/processed/all_screened_papers.csv")

    # Generate PRISMA Flow Diagram
    try:
        dot = graphviz.Digraph(comment="PRISMA Flow Diagram")
        dot.attr(rankdir="TB", size="8,10")

        # Identification
        dot.node('A', f'Records identified through\\ndatabase searching\\n(n = {initial_counts.get("api", 0)})\\nOpenAlex: {initial_counts.get("openalex", 0)}\\nPubMed: {initial_counts.get("pubmed", 0)}', shape='box')
        dot.node('B', f'Additional records identified\\nthrough other sources\\n(n = {initial_counts.get("manual", 0)})', shape='box')
        dot.node(
            "C",
            f"Records after duplicates removed\\n(n = {screened_count})",
            shape="box",
        )

        dot.edge("A", "C")
        dot.edge("B", "C")

        # Screening
        dot.node("D", f"Records screened\\n(n = {screened_count})", shape="box")
        dot.node("E", f"Records excluded\\n(n = {excluded_count})", shape="box")

        dot.edge("C", "D")
        dot.edge("D", "E")

        # Included
        dot.node("F", f"Records included\\n(n = {included_count})", shape="box")
        dot.node("G", f'Records marked "Not Sure"\\n(n = {notsure_count})', shape="box")

        dot.edge("D", "F")
        dot.edge("D", "G")

        # Render
        dot.render("data/processed/prisma_flowchart", format="png", cleanup=True)
        print("PRISMA Flowchart generated at data/processed/prisma_flowchart.png")
    except Exception as e:
        print(f"Error generating PRISMA flowchart (is graphviz installed?): {e}")
