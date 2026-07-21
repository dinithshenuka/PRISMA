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
from menus.criteria_menu import criteria_menu
from menus.extraction_menu import extraction_menu


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
        print("  2. Manage Exclusion Criteria")
        print("  3. Start Title/Abstract Screening")
        print("  4. Full-Text Retrieval (Watchdog Session)")
        print("  5. View Import Stats")
        print("  6. Deduplicate papers")
        print("  7. Data Extraction (LLM)")
        print("  8. Back to Main Menu")
        print(border)

        choice = input("\n  Select an option (1-8): ").strip()

        if choice == '1':
            import_menu(project_id, project_name)

        elif choice == '2':
            criteria_menu(project_id, project_name)

        elif choice == '3':
            papers = get_unscreened_papers(project_id)
            run_screening_session(project_id, papers)

        elif choice == '4':
            clear_screen()
            print("\n  Full-Text Retrieval & DOI Options:")
            print("    [1] Start Watchdog Session for ✅ Included papers (PRISMA Standard)")
            print("    [2] Start Watchdog Session for ⏭  Unscreened papers")
            print("    [3] Open a single paper ID in browser (Manual check)")
            print("    [0] Back")
            subchoice = input("\n  Select an option: ").strip()
            if subchoice == '1':
                from db import get_retrieval_candidates
                from retrieval import run_watchdog_retrieval_session
                candidates = get_retrieval_candidates(project_id, stage_filter='title_included')
                run_watchdog_retrieval_session(project_id, project_name, candidates, stage_label="Included")
            elif subchoice == '2':
                from db import get_retrieval_candidates
                from retrieval import run_watchdog_retrieval_session
                candidates = get_retrieval_candidates(project_id, stage_filter='unscreened')
                run_watchdog_retrieval_session(project_id, project_name, candidates, stage_label="Unscreened")
            elif subchoice == '3':
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

        elif choice == '5':
            stats_menu(project_id, project_name)

        elif choice == '6':
            dedup_menu(project_id, project_name)

        elif choice == '7':
            extraction_menu(project_id, project_name)

        elif choice == '8':
            break
