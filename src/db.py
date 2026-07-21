"""
db.py — Database layer for the PRISMA Pipeline Manager.
Handles all SQLite connection, schema initialization, and query functions.
"""

import sqlite3
import os
import re
import difflib
import unicodedata

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, 'data', 'prisma.db')


def get_db() -> sqlite3.Connection:
    """Return a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the database and create tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            description TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS papers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL,
            title       TEXT,
            authors     TEXT,
            abstract    TEXT,
            doi         TEXT,
            year        INTEGER,
            source_db   TEXT,
            stage       TEXT DEFAULT 'unscreened',
            pdf_path    TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')

    # Migration: add source_db column to existing databases that predate it
    existing_columns = {row[1] for row in cursor.execute("PRAGMA table_info(papers)")}
    if 'source_db' not in existing_columns:
        cursor.execute("ALTER TABLE papers ADD COLUMN source_db TEXT")

    # Migration: add exclusion_reason column
    if 'exclusion_reason' not in existing_columns:
        cursor.execute("ALTER TABLE papers ADD COLUMN exclusion_reason TEXT")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exclusion_criteria (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL,
            reason      TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS extraction_schema (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL,
            column_name TEXT NOT NULL,
            description TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')

    conn.commit()
    conn.close()


# --- Project Operations ---

def create_project(name: str, desc: str) -> int:
    """Insert a new project and return its ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO projects (name, description) VALUES (?, ?)",
        (name, desc)
    )
    project_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return project_id


def get_all_projects() -> list:
    """Return all projects ordered by most recently created."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, created_at FROM projects ORDER BY created_at DESC")
    projects = cursor.fetchall()
    conn.close()
    return projects


def get_project_by_id(project_id: int):
    """Return a single project row by ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()
    conn.close()
    return project


# --- Paper Operations ---

def insert_papers(project_id: int, papers: list[dict], source_db: str) -> int:
    """
    Bulk insert a list of paper dicts into the database.
    Returns the count of inserted rows.
    """
    conn = get_db()
    cursor = conn.cursor()
    count = 0
    for paper in papers:
        if not paper.get('title'):
            continue
        cursor.execute('''
            INSERT INTO papers (project_id, title, authors, abstract, doi, year, source_db)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            project_id,
            paper.get('title', ''),
            paper.get('authors', ''),
            paper.get('abstract', ''),
            paper.get('doi', ''),
            paper.get('year'),
            source_db,
        ))
        count += 1
    conn.commit()
    conn.close()
    return count


def get_unscreened_papers(project_id: int) -> list:
    """Return all unscreened papers for a given project."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, authors, year, abstract, doi
        FROM papers
        WHERE project_id = ? AND stage = 'unscreened'
    ''', (project_id,))
    papers = cursor.fetchall()
    conn.close()
    return papers


def update_paper_stage(paper_id: int, stage: str) -> None:
    """Update the PRISMA stage for a given paper."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE papers SET stage = ? WHERE id = ?", (stage, paper_id))
    conn.commit()
    conn.close()


def get_stats_by_source(project_id: int) -> list:
    """
    Return per-source-database import statistics for a project.

    Each row contains:
      source_db, total, included, excluded, skipped (unscreened)
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            COALESCE(source_db, 'Unknown') AS source_db,
            COUNT(*)                                                       AS total,
            SUM(CASE WHEN stage IN ('title_included', 'fulltext_retrieved', 'extracted') THEN 1 ELSE 0 END) AS included,
            SUM(CASE WHEN stage = 'title_excluded'  THEN 1 ELSE 0 END)   AS excluded,
            SUM(CASE WHEN stage = 'unscreened'      THEN 1 ELSE 0 END)   AS skipped,
            SUM(CASE WHEN stage = 'duplicate'       THEN 1 ELSE 0 END)   AS duplicates,
            SUM(CASE WHEN stage IN ('fulltext_retrieved', 'extracted') OR (pdf_path IS NOT NULL AND pdf_path != '') THEN 1 ELSE 0 END) AS pdfs_retrieved,
            SUM(CASE WHEN stage = 'extracted'       THEN 1 ELSE 0 END)   AS extracted
        FROM papers
        WHERE project_id = ?
        GROUP BY source_db
        ORDER BY source_db
    ''', (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_paper_list_by_stage(project_id: int, stage: str) -> list:
    """
    Return id, title, authors, year, doi, source_db, exclusion_reason, pdf_path for all papers in a given stage.
    stage can be 'title_included', 'title_excluded', 'unscreened', 'duplicate', or 'fulltext_retrieved'.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, authors, year, doi, source_db, exclusion_reason, pdf_path
        FROM papers
        WHERE project_id = ? AND stage = ?
        ORDER BY source_db, id
    ''', (project_id, stage))
    rows = cursor.fetchall()
    conn.close()
    return rows


def _normalize_title(title: str) -> str:
    """
    Normalise a title for fuzzy comparison:
    lowercase, strip accents, collapse whitespace, remove punctuation.
    """
    # Unicode normalisation → strip combining characters (accents)
    nfkd = unicodedata.normalize('NFKD', title)
    ascii_str = ''.join(c for c in nfkd if not unicodedata.combining(c))
    # lowercase and keep only alphanumeric + spaces
    clean = re.sub(r'[^a-z0-9\s]', '', ascii_str.lower())
    return re.sub(r'\s+', ' ', clean).strip()


def find_duplicate_groups(project_id: int, title_threshold: float = 0.92) -> list[list[dict]]:
    """
    Find groups of duplicate papers for a project.

    Two passes:
      1. Exact DOI match  — papers sharing the same non-empty DOI.
      2. Fuzzy title match — remaining papers whose normalised titles
         score >= title_threshold via difflib.SequenceMatcher.

    Returns a list of groups, where each group is a list of paper dicts
    (id, title, authors, year, doi, source_db, stage).
    Only groups with 2+ members are returned.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, authors, year, doi, source_db, stage
        FROM papers
        WHERE project_id = ? AND stage != 'duplicate'
        ORDER BY id
    ''', (project_id,))
    all_papers = [dict(row) for row in cursor.fetchall()]
    conn.close()

    groups: list[list[dict]] = []
    seen_ids: set[int] = set()

    # ── Pass 1: exact DOI duplicates ─────────────────────────────────────
    doi_map: dict[str, list[dict]] = {}
    for p in all_papers:
        doi = (p['doi'] or '').strip().lower()
        if not doi:
            continue
        doi_map.setdefault(doi, []).append(p)

    for doi, members in doi_map.items():
        if len(members) >= 2:
            groups.append(members)
            for m in members:
                seen_ids.add(m['id'])

    # ── Pass 2: fuzzy title duplicates (papers not already grouped) ───────
    remaining = [p for p in all_papers if p['id'] not in seen_ids]

    # Build normalised titles once
    norm_titles = [(p, _normalize_title(p['title'] or '')) for p in remaining]

    matched: set[int] = set()
    for i, (pi, ni) in enumerate(norm_titles):
        if pi['id'] in matched or not ni:
            continue
        group = [pi]
        for j, (pj, nj) in enumerate(norm_titles):
            if i == j or pj['id'] in matched or not nj:
                continue
            ratio = difflib.SequenceMatcher(None, ni, nj).ratio()
            if ratio >= title_threshold:
                group.append(pj)
                matched.add(pj['id'])
        if len(group) >= 2:
            matched.add(pi['id'])
            groups.append(group)

    return groups


def mark_papers_as_duplicate(paper_ids: list[int]) -> None:
    """Set stage = 'duplicate' for each paper ID in the list."""
    if not paper_ids:
        return
    conn = get_db()
    cursor = conn.cursor()
    cursor.executemany(
        "UPDATE papers SET stage = 'duplicate' WHERE id = ?",
        [(pid,) for pid in paper_ids],
    )
    conn.commit()
    conn.close()


def get_doi_by_paper_id(paper_id: int) -> str | None:
    """Return the DOI string for a given paper ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT doi FROM papers WHERE id = ?", (paper_id,))
    row = cursor.fetchone()
    conn.close()
    return row['doi'] if row else None


# --- Exclusion Criteria & Reasoning ---

def add_exclusion_criterion(project_id: int, reason: str) -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO exclusion_criteria (project_id, reason) VALUES (?, ?)", (project_id, reason))
    conn.commit()
    conn.close()

def get_exclusion_criteria(project_id: int) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, reason FROM exclusion_criteria WHERE project_id = ? ORDER BY id", (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_exclusion_criterion(criterion_id: int) -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM exclusion_criteria WHERE id = ?", (criterion_id,))
    conn.commit()
    conn.close()

def update_paper_exclusion(paper_id: int, reason: str) -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE papers SET stage = 'title_excluded', exclusion_reason = ? WHERE id = ?", (reason, paper_id))
    conn.commit()
    conn.close()

def get_exclusion_reasons_stats(project_id: int) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COALESCE(exclusion_reason, 'No reason provided') AS reason, COUNT(*) as count
        FROM papers
        WHERE project_id = ? AND stage = 'title_excluded'
        GROUP BY exclusion_reason
        ORDER BY count DESC, reason
    ''', (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_project_dir(project_id: int, project_name: str) -> str:
    """Return the canonical import directory path for a project."""
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', project_name).strip('_').lower()
    if not safe_name:
        safe_name = "project"
    return os.path.join(BASE_DIR, 'data', 'imports', f"{safe_name}_{project_id}")


def get_project_pdf_dir(project_id: int, project_name: str) -> str:
    """Return the canonical PDF download directory path for a project."""
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', project_name).strip('_').lower()
    if not safe_name:
        safe_name = "project"
    return os.path.join(BASE_DIR, 'data', 'pdfs', f"{safe_name}_{project_id}")


def get_retrieval_candidates(project_id: int, stage_filter: str = 'title_included') -> list:
    """Return papers eligible for full-text PDF retrieval filtered by stage."""
    conn = get_db()
    cursor = conn.cursor()
    if stage_filter == 'all':
        cursor.execute('''
            SELECT id, title, authors, year, doi, source_db, stage, pdf_path
            FROM papers
            WHERE project_id = ?
              AND stage IN ('title_included', 'unscreened')
              AND (pdf_path IS NULL OR pdf_path = '')
              AND doi IS NOT NULL AND doi != ''
            ORDER BY CASE WHEN stage = 'title_included' THEN 0 ELSE 1 END, id
        ''', (project_id,))
    else:
        cursor.execute('''
            SELECT id, title, authors, year, doi, source_db, stage, pdf_path
            FROM papers
            WHERE project_id = ?
              AND stage = ?
              AND (pdf_path IS NULL OR pdf_path = '')
              AND doi IS NOT NULL AND doi != ''
            ORDER BY id
        ''', (project_id, stage_filter))
    rows = cursor.fetchall()
    conn.close()
    return rows


def update_paper_pdf(paper_id: int, pdf_path: str, stage: str = 'fulltext_retrieved') -> None:
    """Set the pdf_path and stage for a paper upon successful retrieval."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE papers SET pdf_path = ?, stage = ? WHERE id = ?", (pdf_path, stage, paper_id))
    conn.commit()
    conn.close()


# --- Extraction Schema Operations ---

def add_extraction_column(project_id: int, column_name: str, description: str) -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO extraction_schema (project_id, column_name, description) VALUES (?, ?, ?)", (project_id, column_name, description))
    conn.commit()
    conn.close()

def get_extraction_schema(project_id: int) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, column_name, description FROM extraction_schema WHERE project_id = ? ORDER BY id", (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_extraction_column(column_id: int) -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM extraction_schema WHERE id = ?", (column_id,))
    conn.commit()
    conn.close()
