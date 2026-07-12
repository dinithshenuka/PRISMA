"""
retrieval.py — Interactive Full-Text PDF Retrieval Watchdog Session.
Monitors ~/Downloads for newly completed PDFs while you browse paywalled DOIs,
auto-renames them cleanly, moves them to project storage, and links them in sqlite.
"""

import os
import sys
import time
import shutil
import re
import select
import webbrowser
from pathlib import Path

from db import get_project_pdf_dir, update_paper_pdf
from menus.utils import clear_screen, pause


def _clean_filename(authors: str | None, year: int | None, title: str | None, paper_id: int) -> str:
    """Generate a clean, standardised filename: Author_Year_CleanTitle.pdf"""
    # 1. Author
    author_clean = "Paper"
    if authors:
        # Extract first surname before comma or 'and'
        first_part = re.split(r'[,;]|\band\b|\bet al\b', authors, flags=re.IGNORECASE)[0].strip()
        first_part = re.sub(r'[^a-zA-Z0-9]', '', first_part)
        if first_part:
            author_clean = first_part

    # 2. Year
    year_clean = str(year) if year else "n.d."

    # 3. Title (first 4-5 significant words)
    title_clean = f"ID_{paper_id}"
    if title:
        words = re.findall(r'[a-zA-Z0-9]+', title)
        if words:
            title_clean = "_".join(words[:5])

    return f"{author_clean}_{year_clean}_{title_clean}.pdf"


def _is_download_stable(pdf_path: Path) -> bool:
    """Check if a PDF file is completely finished downloading and not a temporary partial file."""
    if not pdf_path.exists() or not pdf_path.is_file():
        return False

    # Ignore hidden system files
    if pdf_path.name.startswith('.'):
        return False

    # Check for accompanying browser temporary files
    download_dir = pdf_path.parent
    for ext in ('.crdownload', '.download', '.part', '.tmp'):
        if (download_dir / (pdf_path.name + ext)).exists() or pdf_path.name.endswith(ext):
            return False

    try:
        size1 = pdf_path.stat().st_size
        if size1 == 0:
            return False
        time.sleep(0.5)
        size2 = pdf_path.stat().st_size
        return size1 == size2 and size1 > 0
    except OSError:
        return False


def run_watchdog_retrieval_session(project_id: int, project_name: str, candidates: list) -> None:
    """Run the interactive watchdog loop over eligible candidate papers."""
    if not candidates:
        clear_screen()
        print(f"\n  [!] No eligible papers pending Full-Text Retrieval for '{project_name}'.")
        print("      (Papers must have a valid DOI and be either Included or Unscreened without a PDF.)")
        pause()
        return

    target_dir = get_project_pdf_dir(project_id, project_name)
    os.makedirs(target_dir, exist_ok=True)
    download_dir = Path(os.path.expanduser("~/Downloads"))

    total = len(candidates)
    retrieved_count = 0
    skipped_count = 0

    for idx, p in enumerate(candidates, start=1):
        clear_screen()
        doi = p['doi'].strip() if p['doi'] else ''
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
            if doi.lower().startswith(prefix):
                doi = doi[len(prefix):]
        url = f"https://doi.org/{doi}"

        target_filename = _clean_filename(p['authors'], p['year'], p['title'], p['id'])

        print("═" * 80)
        print(f"  PRISMA Full-Text Retrieval Watchdog | Project: {project_name}")
        print(f"  Progress: Paper {idx} of {total}  (Retrieved: {retrieved_count} | Skipped: {skipped_count})")
        print("═" * 80)
        print(f"  Paper ID : {p['id']}  [Stage: {p['stage']}]")
        print(f"  Title    : {p['title']}")
        print(f"  Authors  : {p['authors'] or 'N/A'}")
        print(f"  DOI      : {p['doi']}")
        print(f"  Target   : {target_filename}")
        print("─" * 80)

        if not download_dir.exists():
            print(f"  [!] Download directory '{download_dir}' not found. Cannot watch.")
            pause()
            return

        # Take snapshot of existing PDFs in ~/Downloads
        snapshot_before = {f.name for f in download_dir.glob("*.pdf") if f.is_file()}

        print(f"\n  Opening browser to: {url} ...")
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"  [!] Failed to open browser: {e}")

        print("\n  👀 Watching ~/Downloads for your new PDF download...")
        print("  ┌─────────────────────────────────────────────────────────────┐")
        print("  │  Instructions:                                              │")
        print("  │    1. Log in / authenticate if prompted by the publisher.   │")
        print("  │    2. Click 'Download PDF' on the browser page.             │")
        print("  │    3. The watchdog will auto-detect, rename, and link it!   │")
        print("  │                                                             │")
        print("  │  Commands (type and press Enter):                           │")
        print("  │    s -> Skip this paper (e.g. no access / paywalled)        │")
        print("  │    q -> Quit full-text retrieval session                    │")
        print("  └─────────────────────────────────────────────────────────────┘")

        detected_pdf: Path | None = None

        while True:
            # Non-blocking check for user terminal input
            if select.select([sys.stdin], [], [], 0.5)[0]:
                user_cmd = sys.stdin.readline().strip().lower()
                if user_cmd == 's':
                    print(f"\n  [⏭ ] Skipped Paper ID {p['id']}.")
                    skipped_count += 1
                    time.sleep(0.7)
                    break
                elif user_cmd == 'q':
                    print("\n  [🛑] Exiting Full-Text Retrieval session.")
                    pause()
                    return
                else:
                    print("       [?] Type 's' to Skip or 'q' to Quit session.")

            # Check ~/Downloads for newly finished PDF files
            try:
                current_pdfs = [f for f in download_dir.glob("*.pdf") if f.is_file() and not f.name.startswith('.')]
            except OSError:
                continue

            new_candidates = [f for f in current_pdfs if f.name not in snapshot_before]
            for candidate in new_candidates:
                if _is_download_stable(candidate):
                    detected_pdf = candidate
                    break

            if detected_pdf:
                break

        if detected_pdf:
            dest_path = os.path.join(target_dir, target_filename)
            # Ensure unique filename if collision exists
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(target_filename)
                dest_path = os.path.join(target_dir, f"{base}_{p['id']}{ext}")

            try:
                shutil.move(str(detected_pdf), dest_path)
                update_paper_pdf(p['id'], dest_path, stage='fulltext_retrieved')
                retrieved_count += 1
                print(f"\n  [✅] Download captured!")
                print(f"       Moved to : {dest_path}")
                print(f"       Database : Linked to Paper ID {p['id']} (stage: fulltext_retrieved)")
            except Exception as e:
                print(f"\n  [!] Error moving file '{detected_pdf}': {e}")
                pause()

            time.sleep(1.2)

    clear_screen()
    print("═" * 80)
    print(f"  Full-Text Retrieval Session Complete — {project_name}")
    print("═" * 80)
    print(f"  Total Processed : {total}")
    print(f"  Retrieved       : {retrieved_count}")
    print(f"  Skipped         : {skipped_count}")
    print(f"  PDF Storage     : {target_dir}")
    print("═" * 80)
    pause()
