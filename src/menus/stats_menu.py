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
    '5': 'fulltext_retrieved',
    '6': 'extracted',
}


def _print_summary_table(rows: list, project_name: str) -> None:
    """Render the per-database statistics table."""
    print(f"\n  Import Statistics — {project_name}")
    print("  " + "═" * 72)
    print(f"  {'Database':<20} {'Total':>6}  {'✅ Incl':>8}  {'📄 PDFs':>8}  {'🧠 Extr':>8}  {'❌ Excl':>8}  {'⏭  Skip':>8}")
    print("  " + "─" * 84)

    totals = [0, 0, 0, 0, 0, 0, 0]
    for r in rows:
        pdfs = r.get('pdfs_retrieved', 0)
        extr = r.get('extracted', 0)
        print(
            f"  {r['source_db']:<20} "
            f"{r['total']:>6}  "
            f"{r['included']:>8}  "
            f"{pdfs:>8}  "
            f"{extr:>8}  "
            f"{r['excluded']:>8}  "
            f"{r['skipped']:>8}"
        )
        totals[0] += r['total']
        totals[1] += r['included']
        totals[2] += pdfs
        totals[3] += extr
        totals[4] += r['excluded']
        totals[5] += r['skipped']
        totals[6] += r['duplicates']

    print("  " + "─" * 84)
    print(
        f"  {'TOTAL':<20} "
        f"{totals[0]:>6}  "
        f"{totals[1]:>8}  "
        f"{totals[2]:>8}  "
        f"{totals[3]:>8}  "
        f"{totals[4]:>8}  "
        f"{totals[5]:>8}"
    )
    print("  " + "═" * 84)

    if totals[6] > 0:
        print(f"\n  🔁 Total Duplicates Removed: {totals[6]}")


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
            
            reason_str = ""
            if 'exclusion_reason' in p.keys() and p['exclusion_reason']:
                reason_str = f" | Excluded: {p['exclusion_reason']}"
            if 'pdf_path' in p.keys() and p['pdf_path']:
                import os
                reason_str += f" | PDF: {os.path.basename(p['pdf_path'])}"
                
            print(f"        {p['authors'] or '':<40}  {p['year'] or '----'}  "
                  f"DOI: {p['doi'] or 'N/A'}{reason_str}")
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
        print("    [1] ✅ Included papers (No PDF)")
        print("    [2] ❌ Excluded papers")
        print("    [3] ⏭  Skipped / Unscreened papers")
        print("    [4] 🔁 Duplicate papers")
        print("    [5] 📄 Full-Text PDF Saved")
        print("    [6] 🧠 Data Extracted")
        print("    [0] Back")

        choice = input("\n  Select an option: ").strip()

        if choice == '0':
            return

        if choice not in _DRILL_OPTIONS:
            print("  [!] Invalid selection.")
            pause()
            continue

        stage = _DRILL_OPTIONS[choice]
        
        if stage == 'title_excluded':
            from db import get_exclusion_reasons_stats
            reasons = get_exclusion_reasons_stats(project_id)
            if reasons:
                clear_screen()
                print(f"\n  Exclusion Reasons Breakdown — {project_name}")
                print("  " + "═" * 60)
                for r in reasons:
                    print(f"  {r['reason']:<40} {r['count']:>8}")
                print("  " + "═" * 60)
                pause()
                
        label, icon = STAGE_LABELS[stage]
        papers = get_paper_list_by_stage(project_id, stage)
        _print_paper_list(papers, label, icon, project_name)
