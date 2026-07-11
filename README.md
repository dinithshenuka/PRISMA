# PRISMA

A CLI tool for running a [PRISMA](https://www.prisma-statement.org/) systematic literature review — import papers from multiple academic databases, screen by title/abstract, and track full-text retrieval, all from the terminal.

## PRISMA 2020 Documents

- [Checklist](https://www.prisma-statement.org/prisma-2020-checklist)
- [Expanded checklist](https://www.prisma-statement.org/prisma-2020-expanded-checklist)
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

1. **Create a project** — each systematic review gets its own project and isolated database records.
2. **Import papers** — drop exported `.csv` or `.ris` files into `data/imports/<project_name>/`. The app auto-detects the source database and parses accordingly.
3. **Screen by title/abstract** — go through papers one-by-one and mark each as `include`, `exclude`, or `skip`. You can open the DOI in your browser mid-session.
4. **Full-text retrieval** — open any paper's DOI directly from the project menu to track down PDFs.

---

## Supported Databases

| Database | Format |
|---|---|
| PubMed | `.ris` |
| Scopus | `.csv` |
| Web of Science | `.ris` |
| IEEE Xplore | `.csv` |
| ACM Digital Library | `.csv` |
| Springer | `.csv` |

---

## Folder Structure

```
PRISMA/
├── src/
│   ├── prisma_cli.py       # Entry point — all menus and UI
│   ├── db.py               # SQLite database layer
│   ├── screening.py        # Interactive screening session logic
│   └── importers/
│       ├── base.py         # Shared CSV/RIS parsing logic
│       ├── pubmed.py
│       ├── scopus.py
│       ├── wos.py
│       ├── ieee.py
│       ├── acm.py
│       └── springer.py
├── data/
│   ├── prisma.db           # Local SQLite database (auto-created)
│   └── imports/
│       └── <project>/      # Drop your exported files here
├── archive/                # Old Flask-based version (not maintained)
└── Makefile
```

---

## Paper Stages

Each paper moves through these stages as you screen:

| Stage | Meaning |
|---|---|
| `unscreened` | Not yet reviewed |
| `title_included` | Passed title/abstract screening |
| `title_excluded` | Rejected at title/abstract stage |
