"""
menus/__init__.py — Public API for the PRISMA CLI menu package.

Import from here instead of individual submodules so internal layout
can change without breaking callers.
"""

from .import_menu import import_menu
from .stats_menu import stats_menu
from .dedup_menu import dedup_menu
from .project_menu import project_menu

__all__ = [
    "import_menu",
    "stats_menu",
    "dedup_menu",
    "project_menu",
]
