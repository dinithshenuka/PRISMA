"""
menus/project_menu.py — Per-project navigation menu.

Wires together all sub-menus for a single open project.
"""

import webbrowser

from db import get_unscreened_papers, get_doi_by_paper_id
from screening import run_screening_session
from menus.utils import clear_screen, pause
from menus.import_menu import import_menu
from menus.stats_menu import stats_menu
from menus.dedup_menu import dedup_menu


def _open_doi_in_browser(doi: str) -> None:
    """Strip known DOI prefixes and open the canonical doi.org URL."""
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    url = f"https://doi.org/{doi}"
    print(f"  Opening {url} ...")
    webbrowser.open(url)


def project_menu(project_id: int, project_name: str) -> None:
    """Main menu for an open project."""
    border = "=" * (len(project_name) + 13)

    while True:
        clear_screen()
        print(border)
        print(f"=== PRISMA | {project_name} ===")
        print(border)
        print("  1. Import papers (CSV or RIS)")
        print("  2. Start Title/Abstract Screening")
        print("  3. Open a paper DOI in browser")
        print("  4. View Import Stats")
        print("  5. Deduplicate papers")
        print("  6. Back to Main Menu")
        print(border)

        choice = input("\n  Select an option (1-6): ").strip()

        if choice == '1':
            import_menu(project_id, project_name)

        elif choice == '2':
            papers = get_unscreened_papers(project_id)
            run_screening_session(papers)

        elif choice == '3':
            try:
                pid = int(input("\n  Enter the paper's Database ID: ").strip())
                doi = get_doi_by_paper_id(pid)
                if not doi:
                    print("  [!] No DOI found for that paper ID.")
                else:
                    _open_doi_in_browser(doi)
            except ValueError:
                print("  [!] Invalid ID.")
            pause()

        elif choice == '4':
            stats_menu(project_id, project_name)

        elif choice == '5':
            dedup_menu(project_id, project_name)

        elif choice == '6':
            break
