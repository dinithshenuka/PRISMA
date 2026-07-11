# PRISMA Pipeline Manager

An interactive CLI tool to manage a PRISMA systematic literature review workflow using a local SQLite database.

## Folder Structure
- `src/` - Contains the Python source code (`prisma_cli.py`)
- `data/` - Contains the local SQLite database (`prisma.db`)
- `data/imports/` - A place to store your exported `.ris` and `.csv` files. The app automatically creates a subfolder here for each new project.
- `archive/` - Old application code.

## Usage

This tool is entirely menu-driven and interactive. You only ever need to run ONE command to launch the app:

```bash
python3 src/prisma_cli.py
```

The app will start a text-based wizard that allows you to:
1. Create a new review or select an existing one.
2. Interactively import `.csv` and `.ris` files (it will even auto-detect them if you put them in the correct `data/imports/project_X/` folder).
3. Conduct interactive Title/Abstract screening.
4. Auto-open DOIs in your browser for full-text PDF retrieval.
