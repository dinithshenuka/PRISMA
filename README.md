# PRISMA

A CLI tool for running a [PRISMA](https://www.prisma-statement.org/) systematic literature review (SLR) — import papers from multiple academic databases, deduplicate, screen by title/abstract, and track full-text retrieval, all from the terminal with zero external dependencies.

## PRISMA 2020 Documents

- [Checklist](https://www.prisma-statement.org/s/PRISMA_2020_checklist-ez8t.docx)
- [Expanded checklist](https://static1.squarespace.com/static/65b880e13b6ca75573dfe217/t/67e61ce66cee8e7f7c59396f/1743133927578/PRISMA_2020_expanded_checklist.pdf)
- [Flow diagram](https://www.prisma-statement.org/prisma-2020-flow-diagram)
- [Statement paper](https://www.prisma-statement.org/prisma-2020-statement)
- [Explanation and elaboration paper](https://www.prisma-statement.org/prisma-2020-explanation-elaboration)

---

## Requirements

- Python 3.10+
- No external packages — pure stdlib only

---

## Usage

```bash
# Option 1: make shortcut
make dev

# Option 2: run directly
python3 src/prisma_cli.py
```

The app is fully menu-driven — no arguments needed.

---

## Workflow

1. **Create a project** — each SLR gets its own project with isolated database records.
2. **Import papers** — drop exported `.csv` or `.ris` files into `data/imports/<project_name>/`. The tool auto-detects the source database and parses accordingly.
3. **Deduplicate** — scan for exact DOI matches and near-identical titles across all imports. Review each duplicate group and choose which copy to keep.
4. **Screen by title/abstract** — go through papers one-by-one and mark each as `include`, `exclude`, or `skip`. Open the DOI in your browser mid-session.
5. **View stats** — see a live breakdown of imported, included, excluded, and skipped counts per database, with drill-down paper lists.
6. **Full-text retrieval** — open any paper's DOI directly from the project menu to track down PDFs.


## Supported Import Formats

| Database            | Format |
|---------------------|--------|
| IEEE Xplore         | `.csv` |
| Scopus              | `.csv` |
| Web of Science      | `.ris` |
| ACM Digital Library | `.ris` |
| Springer            | `.csv` |
| PubMed              | `.ris` |

---

## Paper Stages

Each paper moves through these stages as you work:

| Stage                | Meaning                                      |
|----------------------|----------------------------------------------|
| `unscreened`         | Not yet reviewed                             |
| `title_included`     | Passed title/abstract screening (pending PDF)|
| `fulltext_retrieved` | Full-text PDF successfully captured & linked |
| `title_excluded`     | Rejected at title/abstract stage             |
| `duplicate`          | Flagged as a duplicate and removed from flow |

---

## Folder Structure

```
PRISMA/
├── src/
│   ├── prisma_cli.py       # Entry point — main menu only
│   ├── db.py               # SQLite database layer + all queries
│   ├── screening.py        # Interactive title/abstract screening session
│   ├── retrieval.py        # Interactive full-text PDF retrieval watchdog
│   ├── importers/          # Per-database CSV/RIS parsers
│   │   ├── base.py         #   Shared parsing logic
│   │   ├── ieee.py
│   │   ├── scopus.py
│   │   ├── wos.py
│   │   ├── acm.py
│   │   ├── springer.py
│   │   └── pubmed.py
│   └── menus/              # CLI menu package (one file per screen)
│       ├── __init__.py     #   Public re-exports
│       ├── utils.py        #   Shared helpers (clear_screen, pause, STAGE_LABELS)
│       ├── import_menu.py  #   File selection + import flow
│       ├── stats_menu.py   #   Stats table + drill-down lists
│       ├── dedup_menu.py   #   Deduplication session
│       └── project_menu.py #   Per-project navigation
├── data/
│   ├── prisma.db           # Local SQLite database (auto-created)
│   ├── imports/
│   │   └── <project>/      # Drop your exported database files here
│   └── pdfs/
│       └── <project>/      # Auto-saved and standardized full-text PDFs
└── Makefile
```

---

## Deduplication

The dedup scanner runs two passes automatically:

1. **Exact DOI match** — papers sharing the same DOI (common when the same paper is exported from multiple databases).
2. **Fuzzy title match** — papers whose normalised titles score ≥ 0.92 similarity via `difflib.SequenceMatcher` (catches the same paper published in multiple venues with identical/near-identical titles).

For each group found, you choose which copy to keep — the rest are marked `duplicate` and excluded from screening.
