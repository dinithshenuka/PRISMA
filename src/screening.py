"""
screening.py — Interactive Title/Abstract screening session logic.
"""

import webbrowser
import os
from db import update_paper_stage, get_doi_by_paper_id


def clear_screen() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')


def _open_doi(paper_id: int) -> None:
    """Resolve and open a paper's DOI in the default web browser."""
    doi = get_doi_by_paper_id(paper_id)
    if not doi:
        print("  [!] No DOI available for this paper.")
        return

    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]

    url = f"https://doi.org/{doi}"
    print(f"  Opening {url} in browser...")
    webbrowser.open(url)


def run_screening_session(papers: list) -> None:
    """
    Run an interactive CLI screening session over a list of paper rows.

    Stages applied:
      (i) Include → 'title_included'
      (e) Exclude → 'title_excluded'
      (s) Skip    → no change (stays 'unscreened')
      (q) Quit    → saves progress and exits
    """
    if not papers:
        print("\n  [!] No unscreened papers found for this project.")
        input("\nPress Enter to continue...")
        return

    total = len(papers)
    clear_screen()
    print(f"  Starting screening session — {total} paper(s) to review.\n")

    for idx, paper in enumerate(papers, start=1):
        clear_screen()
        print(f"  Paper {idx} of {total}")
        print("=" * 80)
        print(f"  [{paper['id']}] TITLE:   {paper['title']}")
        print(f"  AUTHORS:  {paper['authors']}")
        print(f"  YEAR:     {paper['year']}  |  DOI: {paper['doi'] or 'N/A'}")
        print("-" * 80)
        print("  ABSTRACT:")
        print(f"  {paper['abstract'] or 'No abstract available.'}")
        print("=" * 80)

        import time
        while True:
            print("\n  (i) Include  |  (e) Exclude  |  (o) Open DOI  |  (s) Skip  |  (q) Quit")
            choice = input("  Your choice: ").strip().lower()

            if choice == 'i':
                update_paper_stage(paper['id'], 'title_included')
                print("  ✓ Included.")
                time.sleep(0.5)
                break
            elif choice == 'e':
                update_paper_stage(paper['id'], 'title_excluded')
                print("  ✗ Excluded.")
                time.sleep(0.5)
                break
            elif choice == 'o':
                _open_doi(paper['id'])
            elif choice == 's':
                print("  → Skipped.")
                time.sleep(0.5)
                break
            elif choice == 'q':
                print("\n  Progress saved. Exiting screening session.")
                input("\nPress Enter to return to menu...")
                return
            else:
                print("  [!] Invalid choice. Please try again.")

    clear_screen()
    print(f"\n  [+] Screening complete! All {total} papers have been reviewed.")
    input("\nPress Enter to return to menu...")
