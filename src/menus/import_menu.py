"""
menus/import_menu.py — Handles the file-selection and paper-import flow.
"""

import os

from db import get_project_dir, insert_papers
from importers import detect_importer
from menus.utils import clear_screen, pause


def _list_files(directory: str, extension: str) -> list[str]:
    """Return sorted filenames with *extension* found inside *directory*."""
    os.makedirs(directory, exist_ok=True)
    return sorted(
        f for f in os.listdir(directory)
        if f.lower().endswith(extension)
    )


def import_menu(project_id: int, project_name: str) -> None:
    """Show available export files in the project folder and handle import."""
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
