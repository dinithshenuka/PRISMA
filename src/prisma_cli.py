#!/usr/bin/env python3
"""
prisma_cli.py — Main entry point for the PRISMA Pipeline Manager.
UI only: menus, user input, and output. All business logic is in other modules.
"""

import sys
import os

# Ensure src/ is on the path so sibling modules resolve correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import (
    init_db,
    create_project,
    get_all_projects,
    get_project_by_id,
    insert_papers,
    get_unscreened_papers,
    get_doi_by_paper_id,
    get_project_dir,
    get_stats_by_source,
    get_paper_list_by_stage,
)
from importers import detect_importer
from screening import run_screening_session
import webbrowser


def clear_screen() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')


def pause() -> None:
    input("\nPress Enter to continue...")


# --- Import Menu ---

def _list_files(directory: str, extension: str) -> list[str]:
    """Return files with the given extension inside a directory."""
    os.makedirs(directory, exist_ok=True)
    return sorted(
        f for f in os.listdir(directory)
        if f.lower().endswith(extension)
    )


def import_menu(project_id: int, project_name: str) -> None:
    """Show available files in the project import folder and handle import."""
    project_dir = get_project_dir(project_id, project_name)
    os.makedirs(project_dir, exist_ok=True)

    files = _list_files(project_dir, '.csv') + _list_files(project_dir, '.ris')

    if not files:
        print(f"\n  [!] No .csv or .ris files found in:")
        print(f"      {project_dir}/")
        print("\n  Please drop your exported files there and try again.")
        pause()
        return

    print(f"\n  Import folder: {project_dir}/")
    print("\n  Available files:")
    for i, filename in enumerate(files, start=1):
        print(f"    [{i}] {filename}")
    print("    [0] Cancel")

    try:
        choice = int(input("\n  Select a file to import: ").strip())
        if choice == 0:
            return
        if not (1 <= choice <= len(files)):
            print("  [!] Invalid selection.")
            pause()
            return
    except ValueError:
        print("  [!] Invalid input.")
        pause()
        return

    filepath = os.path.join(project_dir, files[choice - 1])

    try:
        importer = detect_importer(filepath)
        print(f"\n  Detected source: {importer.SOURCE_NAME}")
        papers = importer.parse(filepath)
        count = insert_papers(project_id, papers, importer.SOURCE_NAME)
        print(f"  [+] Successfully imported {count} paper(s) from {importer.SOURCE_NAME}!")
    except Exception as e:
        print(f"\n  [!] Import failed: {e}")

    pause()


# --- Stats Menu ---

_STAGE_LABELS = {
    'title_included': ('Included', '✅'),
    'title_excluded': ('Excluded', '❌'),
    'unscreened':     ('Skipped / Unscreened', '⏭ '),
}


def stats_menu(project_id: int, project_name: str) -> None:
    """Display import statistics per source database, with drill-down lists."""
    while True:
        clear_screen()
        rows = get_stats_by_source(project_id)

        if not rows:
            print(f"\n  [!] No papers imported yet for '{project_name}'.")
            pause()
            return

        # ── Summary table ───────────────────────────────────────────────────
        print(f"\n  Import Statistics — {project_name}")
        print("  " + "═" * 62)
        print(f"  {'Database':<20} {'Total':>6}  {'✅ Incl':>8}  {'❌ Excl':>8}  {'⏭  Skip':>8}")
        print("  " + "─" * 62)

        totals = [0, 0, 0, 0]  # total, included, excluded, skipped
        for r in rows:
            print(
                f"  {r['source_db']:<20} "
                f"{r['total']:>6}  "
                f"{r['included']:>8}  "
                f"{r['excluded']:>8}  "
                f"{r['skipped']:>8}"
            )
            totals[0] += r['total']
            totals[1] += r['included']
            totals[2] += r['excluded']
            totals[3] += r['skipped']

        print("  " + "─" * 62)
        print(
            f"  {'TOTAL':<20} "
            f"{totals[0]:>6}  "
            f"{totals[1]:>8}  "
            f"{totals[2]:>8}  "
            f"{totals[3]:>8}"
        )
        print("  " + "═" * 62)

        # ── Drill-down options ───────────────────────────────────────────────
        print("\n  View list:")
        print("    [1] ✅ Included papers")
        print("    [2] ❌ Excluded papers")
        print("    [3] ⏭  Skipped / Unscreened papers")
        print("    [0] Back")

        choice = input("\n  Select an option: ").strip()

        if choice == '0':
            return

        stage_map = {
            '1': 'title_included',
            '2': 'title_excluded',
            '3': 'unscreened',
        }

        if choice not in stage_map:
            print("  [!] Invalid selection.")
            pause()
            continue

        stage = stage_map[choice]
        label, icon = _STAGE_LABELS[stage]
        papers = get_paper_list_by_stage(project_id, stage)

        clear_screen()
        print(f"\n  {icon} {label} papers ({len(papers)} total) — {project_name}")
        print("  " + "═" * 80)

        if not papers:
            print("  (none)")
        else:
            for p in papers:
                print(f"  [{p['id']:>3}] [{p['source_db']}] "
                      f"{(p['title'] or 'No title')[:65]}"
                      f"{'...' if len(p['title'] or '') > 65 else ''}")
                print(f"        {p['authors'] or '':<40}  {p['year'] or '----'}  "
                      f"DOI: {p['doi'] or 'N/A'}")
                print()

        print("  " + "═" * 80)
        pause()


# --- Project Menu ---

def project_menu(project_id: int, project_name: str) -> None:
    while True:
        clear_screen()
        border = "=" * (len(project_name) + 13)
        print(f"{border}")
        print(f"=== PRISMA | {project_name} ===")
        print(f"{border}")
        print("  1. Import papers (CSV or RIS)")
        print("  2. Start Title/Abstract Screening")
        print("  3. Open a paper DOI in browser")
        print("  4. View Import Stats")
        print("  5. Back to Main Menu")
        print(border)

        choice = input("\n  Select an option (1-5): ").strip()

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
                    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
                        if doi.startswith(prefix):
                            doi = doi[len(prefix):]
                    url = f"https://doi.org/{doi}"
                    print(f"  Opening {url} ...")
                    webbrowser.open(url)
            except ValueError:
                print("  [!] Invalid ID.")
            pause()

        elif choice == '4':
            stats_menu(project_id, project_name)

        elif choice == '5':
            break


# --- Main Menu ---

def main_menu() -> None:
    init_db()

    while True:
        clear_screen()
        print("╔══════════════════════════════╗")
        print("║   PRISMA Pipeline Manager    ║")
        print("╠══════════════════════════════╣")
        print("║  1. Open existing project    ║")
        print("║  2. Create new project       ║")
        print("║  3. Exit                     ║")
        print("╚══════════════════════════════╝")

        choice = input("\n  Select an option (1-3): ").strip()

        if choice == '1':
            projects = get_all_projects()
            if not projects:
                print("\n  [!] No projects yet. Please create one first.")
                pause()
                continue

            print("\n  --- Your Projects ---")
            for p in projects:
                print(f"    [{p['id']}] {p['name']}")
            print("    [0] Cancel")

            try:
                pid = int(input("\n  Enter Project ID: ").strip())
                if pid == 0:
                    continue
                project = get_project_by_id(pid)
                if project:
                    project_menu(project['id'], project['name'])
                else:
                    print("  [!] Invalid Project ID.")
                    pause()
            except ValueError:
                print("  [!] Invalid input.")
                pause()

        elif choice == '2':
            print("\n  --- Create New Project ---")
            name = input("  Project Name: ").strip()
            if not name:
                print("  [!] Name cannot be empty.")
                pause()
                continue
            desc = input("  Description (optional): ").strip()

            pid = create_project(name, desc)
            project_dir = get_project_dir(pid, name)
            os.makedirs(project_dir, exist_ok=True)

            print(f"\n  [+] Project '{name}' created! ID: {pid}")
            print(f"  [+] Drop your export files into:")
            print(f"      {project_dir}/")
            pause()
            project_menu(pid, name)

        elif choice == '3':
            clear_screen()
            print("  Goodbye!\n")
            sys.exit(0)


if __name__ == '__main__':
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n  Interrupted. Goodbye!")
        sys.exit(0)
