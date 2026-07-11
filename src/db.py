"""
db.py — Database layer for the PRISMA Pipeline Manager.
Handles all SQLite connection, schema initialization, and query functions.
"""

import sqlite3
import os
import re

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


def get_doi_by_paper_id(paper_id: int) -> str | None:
    """Return the DOI string for a given paper ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT doi FROM papers WHERE id = ?", (paper_id,))
    row = cursor.fetchone()
    conn.close()
    return row['doi'] if row else None


def get_project_dir(project_id: int, project_name: str) -> str:
    """Return the canonical import directory path for a project."""
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', project_name).strip('_').lower()
    if not safe_name:
        safe_name = "project"
    return os.path.join(BASE_DIR, 'data', 'imports', f"{safe_name}_{project_id}")
