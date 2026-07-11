"""
menus/stats_menu.py — Import statistics screen with per-database breakdown
and drill-down paper lists.
"""

from db import get_stats_by_source, get_paper_list_by_stage
from menus.utils import clear_screen, pause, STAGE_LABELS

# Stage options shown in the drill-down sub-menu
_DRILL_OPTIONS: dict[str, str] = {
    '1': 'title_included',
    '2': 'title_excluded',
    '3': 'unscreened',
    '4': 'duplicate',
}


def _print_summary_table(rows: list, project_name: str) -> None:
    """Render the per-database statistics table."""
    print(f"\n  Import Statistics — {project_name}")
    print("  " + "═" * 74)
    print(f"  {'Database':<20} {'Total':>6}  {'✅ Incl':>8}  {'❌ Excl':>8}  {'⏭  Skip':>8}  {'🔁 Dup':>8}")
    print("  " + "─" * 74)

    totals = [0, 0, 0, 0, 0]
    for r in rows:
        print(
            f"  {r['source_db']:<20} "
            f"{r['total']:>6}  "
            f"{r['included']:>8}  "
            f"{r['excluded']:>8}  "
            f"{r['skipped']:>8}  "
            f"{r['duplicates']:>8}"
        )
        totals[0] += r['total']
        totals[1] += r['included']
        totals[2] += r['excluded']
        totals[3] += r['skipped']
        totals[4] += r['duplicates']

    print("  " + "─" * 74)
    print(
        f"  {'TOTAL':<20} "
        f"{totals[0]:>6}  "
        f"{totals[1]:>8}  "
        f"{totals[2]:>8}  "
        f"{totals[3]:>8}  "
        f"{totals[4]:>8}"
    )
    print("  " + "═" * 74)


def _print_paper_list(papers: list, label: str, icon: str, project_name: str) -> None:
    """Render the full paper list for a given stage."""
    clear_screen()
    print(f"\n  {icon} {label} papers ({len(papers)} total) — {project_name}")
    print("  " + "═" * 80)

    if not papers:
        print("  (none)")
    else:
        for p in papers:
            title = p['title'] or 'No title'
            truncated = title[:65] + ('...' if len(title) > 65 else '')
            print(f"  [{p['id']:>3}] [{p['source_db']}] {truncated}")
            print(f"        {p['authors'] or '':<40}  {p['year'] or '----'}  "
                  f"DOI: {p['doi'] or 'N/A'}")
            print()

    print("  " + "═" * 80)
    pause()


def stats_menu(project_id: int, project_name: str) -> None:
    """Display import statistics per source database, with drill-down lists."""
    while True:
        clear_screen()
        rows = get_stats_by_source(project_id)

        if not rows:
            print(f"\n  [!] No papers imported yet for '{project_name}'.")
            pause()
            return

        _print_summary_table(rows, project_name)

        print("\n  View list:")
        print("    [1] ✅ Included papers")
        print("    [2] ❌ Excluded papers")
        print("    [3] ⏭  Skipped / Unscreened papers")
        print("    [4] 🔁 Duplicate papers")
        print("    [0] Back")

        choice = input("\n  Select an option: ").strip()

        if choice == '0':
            return

        if choice not in _DRILL_OPTIONS:
            print("  [!] Invalid selection.")
            pause()
            continue

        stage = _DRILL_OPTIONS[choice]
        label, icon = STAGE_LABELS[stage]
        papers = get_paper_list_by_stage(project_id, stage)
        _print_paper_list(papers, label, icon, project_name)
