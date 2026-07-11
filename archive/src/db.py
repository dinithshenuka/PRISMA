import sqlite3
import os

DB_PATH = "data/prisma.db"


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT UNIQUE,
            llm_model TEXT,
            max_results INTEGER,
            openalex_query TEXT,
            pubmed_query TEXT,
            inclusion_criteria TEXT,
            exclusion_criteria TEXT,
            year_start INTEGER,
            year_end INTEGER
        )
    """)
    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN year_start INTEGER DEFAULT 2020")
        cursor.execute("ALTER TABLE projects ADD COLUMN year_end INTEGER DEFAULT 2026")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


def get_project_config(project_name="Default_Project"):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM projects WHERE project_name = ?", (project_name,))
    row = cursor.fetchone()
    conn.close()

    if row:
        config = dict(row)
        config["inclusion_criteria"] = (
            config["inclusion_criteria"].split("\n")
            if config["inclusion_criteria"]
            else []
        )
        config["exclusion_criteria"] = (
            config["exclusion_criteria"].split("\n")
            if config["exclusion_criteria"]
            else []
        )
        config["search_queries"] = {
            "openalex": config.pop("openalex_query"),
            "pubmed": config.pop("pubmed_query"),
        }
        return config
    else:
        # Return default structure if it doesn't exist
        return {
            "project_name": project_name,
            "llm_model": "llama-3.1-8b-instant",
            "max_results": 10,
            "search_queries": {"openalex": "", "pubmed": ""},
            "inclusion_criteria": [],
            "exclusion_criteria": [],
            "year_start": 2020,
            "year_end": 2026
        }


def save_project_config(config):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    inc_str = "\n".join(config.get("inclusion_criteria", []))
    exc_str = "\n".join(config.get("exclusion_criteria", []))

    cursor.execute(
        """
        INSERT OR REPLACE INTO projects (
            id, project_name, llm_model, max_results, openalex_query, pubmed_query, inclusion_criteria, exclusion_criteria, year_start, year_end
        ) VALUES (
            (SELECT id FROM projects WHERE project_name = ?),
            ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """,
        (
            config.get("project_name"),
            config.get("project_name", "Default_Project"),
            config.get("llm_model", "llama-3.1-8b-instant"),
            config.get("max_results", 10),
            config.get("search_queries", {}).get("openalex", ""),
            config.get("search_queries", {}).get("pubmed", ""),
            inc_str,
            exc_str,
            config.get("year_start", 2020),
            config.get("year_end", 2026)
        ),
    )
    conn.commit()
    conn.close()
