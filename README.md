# PRISMA Pipeline Manager

A simple CLI tool to manage a PRISMA systematic literature review workflow using a local SQLite database.

## Folder Structure
- `src/` - Contains the Python source code (`prisma_cli.py`)
- `data/` - Contains the local SQLite database (`prisma.db`)
- `data/imports/` - A recommended place to store your exported `.ris` and `.csv` files before importing.
- `archive/` - Old application code.

## Usage

Run all commands using the script located in `src/`.

### Initialize Database
*(Already done for you!)*
```bash
python3 src/prisma_cli.py init-db
```

### Create a Project
```bash
python3 src/prisma_cli.py create-project "My New Review" --desc "A systematic review on X"
```

### Import Search Results
You can import `.csv` or `.ris` files. 
```bash
# Example CSV import
python3 src/prisma_cli.py import-csv 1 "data/imports/my_results.csv"

# Example RIS import
python3 src/prisma_cli.py import-ris 1 "data/imports/my_results.ris"
```

### Screen Papers
Start an interactive Title/Abstract screening session.
```bash
python3 src/prisma_cli.py screen 1
```

### Open a Paper's DOI
Automatically open the paper's DOI link in your default web browser to download the full-text PDF.
```bash
python3 src/prisma_cli.py open-doi 5
```
