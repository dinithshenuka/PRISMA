"""
menus/dedup_menu.py — Interactive deduplication session.

Scans for duplicate papers (exact DOI or fuzzy title) and lets the user
choose which copy to keep; the rest are marked stage='duplicate'.
"""

from db import find_duplicate_groups, mark_papers_as_duplicate
from menus.utils import clear_screen, pause


# ── Paper display helper ──────────────────────────────────────────────────────

def _print_paper_row(idx: int, paper: dict) -> None:
    """Print one paper entry inside a duplicate group."""
    title = (paper['title'] or 'No title')[:68]
    if len(paper['title'] or '') > 68:
        title += '...'
    print(f"   [{idx}] ID={paper['id']:>3}  [{paper['source_db']}]  stage={paper['stage']}")
    print(f"       Title  : {title}")
    print(f"       Authors: {(paper['authors'] or 'N/A')[:70]}")
    print(f"       Year   : {paper['year'] or '----'}   DOI: {paper['doi'] or 'N/A'}")
    print()


# ── Session summary ───────────────────────────────────────────────────────────

def _print_session_summary(total: int, resolved: int, skipped: int, marked_ids: list[int]) -> None:
    clear_screen()
    print("\n  " + "═" * 60)
    print("  🔁 Deduplication Session Complete")
    print("  " + "─" * 60)
    print(f"  Groups found     : {total}")
    print(f"  Groups resolved  : {resolved}")
    print(f"  Groups skipped   : {skipped}")
    print(f"  Papers marked    : {len(marked_ids)} as 'duplicate'")
    if marked_ids:
        print(f"  Marked IDs       : {marked_ids}")
    print("  " + "═" * 60)
    pause()


# ── Per-group review ──────────────────────────────────────────────────────────

def _review_group(
    g_idx: int,
    total_groups: int,
    group: list[dict],
    resolved: int,
    skipped: int,
) -> tuple[str, list[int]]:
    """
    Show one duplicate group and ask the user what to do.

    Returns:
        action  — 'keep' | 'skip' | 'quit'
        ids     — paper IDs marked as duplicate (empty for skip/quit)
    """
    while True:
        clear_screen()
        print(f"\n  🔁 Duplicate Group {g_idx} of {total_groups}  "
              f"({resolved} resolved, {skipped} skipped so far)")
        print("  " + "═" * 80)

        for idx, paper in enumerate(group, start=1):
            _print_paper_row(idx, paper)

        print("  " + "─" * 80)
        print("  Which paper is the original/best copy? (The rest will be marked 'duplicate')")
        print("  Enter NUMBER to keep  |  [s] Skip (do nothing to this group)  |  [q] Quit")

        choice = input("\n  Your choice: ").strip().lower()

        if choice == 'q':
            return 'quit', []

        if choice == 's':
            return 'skip', []

        try:
            keep_idx = int(choice)
            if not (1 <= keep_idx <= len(group)):
                raise ValueError
        except ValueError:
            print("  [!] Invalid input. Enter a number, 's', or 'q'.")
            input("  Press Enter to try again...")
            continue

        keep_paper = group[keep_idx - 1]
        to_mark = [p['id'] for p in group if p['id'] != keep_paper['id']]
        mark_papers_as_duplicate(to_mark)

        import time
        print(f"\n  ✅ Kept ID={keep_paper['id']}. "
              f"Marked {len(to_mark)} paper(s) as duplicate.")
        time.sleep(0.75)  # Brief pause to show success before auto-advancing
        return 'keep', to_mark


# ── Public entry point ────────────────────────────────────────────────────────

def dedup_menu(project_id: int, project_name: str) -> None:
    """
    Interactive deduplication session.

    Scans for duplicate groups (exact DOI then fuzzy title), then walks
    the user through each group one-by-one.
    """
    clear_screen()
    print(f"\n  🔍 Scanning for duplicates in '{project_name}'...")

    groups = find_duplicate_groups(project_id)

    if not groups:
        print("\n  ✅ No duplicates found! All papers are unique.")
        pause()
        return

    total_groups = len(groups)
    resolved     = 0
    skipped      = 0
    marked_ids: list[int] = []

    for g_idx, group in enumerate(groups, start=1):
        action, ids = _review_group(g_idx, total_groups, group, resolved, skipped)

        if action == 'quit':
            print(f"\n  ⚡ Quit early — {resolved} group(s) resolved, "
                  f"{len(marked_ids)} paper(s) marked as duplicate.")
            pause()
            return
        elif action == 'skip':
            skipped += 1
        elif action == 'keep':
            resolved += 1
            marked_ids.extend(ids)

    _print_session_summary(total_groups, resolved, skipped, marked_ids)
