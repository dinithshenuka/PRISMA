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


# --- Project Menu ---

def project_menu(project_id: int, project_name: str) -> None:
    while True:
        clear_screen()
        print(f"=== PRISMA | {project_name} ===")
        print("  1. Import papers (CSV or RIS)")
        print("  2. Start Title/Abstract Screening")
        print("  3. Open a paper DOI in browser")
        print("  4. Back to Main Menu")
        print("=" * (len(project_name) + 13))

        choice = input("\n  Select an option (1-4): ").strip()

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
