"""
menus/utils.py — Shared UI helpers and constants for every menu module.
"""

import os

# Maps a paper's stage value → (human label, icon)
STAGE_LABELS: dict[str, tuple[str, str]] = {
    'title_included':     ('Included (No PDF)',      '✅'),
    'fulltext_retrieved': ('Full-Text PDF Saved',    '📄'),
    'title_excluded':     ('Excluded',               '❌'),
    'unscreened':         ('Skipped / Unscreened',   '⏭ '),
    'duplicate':          ('Duplicates',             '🔁'),
}


def clear_screen() -> None:
    """Clear the terminal screen (cross-platform)."""
    os.system('cls' if os.name == 'nt' else 'clear')


def pause(msg: str = "\nPress Enter to continue...") -> None:
    """Block until the user presses Enter."""
    input(msg)
