#!/usr/bin/env python3
"""
prisma_cli.py — Entry point for the PRISMA Pipeline Manager.

Responsibility: main menu only (project selection / creation / exit).
All sub-menus live in the menus/ package.
"""

import sys
import os

# Ensure src/ is on the path so sibling packages resolve correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import init_db, create_project, get_all_projects, get_project_by_id, get_project_dir
from menus import project_menu
from menus.utils import clear_screen, pause


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
