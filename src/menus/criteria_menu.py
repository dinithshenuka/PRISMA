"""
menus/criteria_menu.py — Manage exclusion criteria for a project.
"""

from db import get_exclusion_criteria, add_exclusion_criterion, delete_exclusion_criterion
from menus.utils import clear_screen, pause


def criteria_menu(project_id: int, project_name: str) -> None:
    """Menu to manage exclusion criteria for a specific project."""
    while True:
        clear_screen()
        print(f"\n  Manage Exclusion Criteria — {project_name}")
        print("  " + "═" * (28 + len(project_name)))
        
        criteria = get_exclusion_criteria(project_id)
        if not criteria:
            print("  (No criteria defined yet. You can use free-text during screening.)")
        else:
            for idx, c in enumerate(criteria, start=1):
                print(f"  [{idx}] {c['reason']}")
        print("  " + "═" * (28 + len(project_name)))

        print("\n  Options:")
        print("    [a] Add new criterion")
        if criteria:
            print("    [d] Delete a criterion")
        print("    [0] Back to project menu")

        choice = input("\n  Select an option: ").strip().lower()

        if choice == '0':
            break
        elif choice == 'a':
            reason = input("  Enter new exclusion reason: ").strip()
            if reason:
                add_exclusion_criterion(project_id, reason)
                print("  ✓ Criterion added.")
            else:
                print("  [!] Reason cannot be empty.")
            import time; time.sleep(0.5)
        elif choice == 'd' and criteria:
            try:
                c_idx = int(input("  Enter criterion number to delete: ").strip())
                if 1 <= c_idx <= len(criteria):
                    c_id = criteria[c_idx - 1]['id']
                    delete_exclusion_criterion(c_id)
                    print("  ✓ Criterion deleted.")
                else:
                    print("  [!] Invalid number.")
            except ValueError:
                print("  [!] Invalid input.")
            import time; time.sleep(0.5)
        else:
            print("  [!] Invalid selection.")
            import time; time.sleep(0.5)
