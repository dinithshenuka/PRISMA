#!/usr/bin/env python3
import sqlite3
import argparse
import csv
import webbrowser
import sys
import re
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, 'data', 'prisma.db')

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(args):
    conn = get_db()
    cursor = conn.cursor()
    
    # Create Projects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create Papers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT,
            authors TEXT,
            abstract TEXT,
            doi TEXT,
            year INTEGER,
            stage TEXT DEFAULT 'unscreened',
            pdf_path TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Initialized database in '{DB_FILE}'")

def create_project(args):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO projects (name, description) VALUES (?, ?)", (args.name, args.desc))
    project_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"Created project '{args.name}' with ID: {project_id}")

def import_csv(args):
    conn = get_db()
    cursor = conn.cursor()
    
    count = 0
    with open(args.file, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # We try to flexibly map common CSV columns
            title = row.get('Title', row.get('title', ''))
            authors = row.get('Authors', row.get('authors', ''))
            abstract = row.get('Abstract', row.get('abstract', ''))
            doi = row.get('DOI', row.get('doi', ''))
            year = row.get('Year', row.get('year', None))
            
            if not title:
                continue
                
            cursor.execute('''
                INSERT INTO papers (project_id, title, authors, abstract, doi, year)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (args.project_id, title, authors, abstract, doi, year))
            count += 1
            
    conn.commit()
    conn.close()
    print(f"Successfully imported {count} papers into project {args.project_id}")

def import_ris(args):
    conn = get_db()
    cursor = conn.cursor()
    
    count = 0
    with open(args.file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    current_paper = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # RIS fields are typically 2 chars, 2 spaces, a dash, a space, then the value
        # e.g., "TI  - The title of the paper"
        match = re.match(r'^([A-Z0-9]{2})\s+-\s+(.*)$', line)
        if match:
            tag, value = match.groups()
            
            if tag == 'TY': # Start of a new reference
                if current_paper:
                    # Save previous paper
                    cursor.execute('''
                        INSERT INTO papers (project_id, title, authors, abstract, doi, year)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        args.project_id, 
                        current_paper.get('title', ''), 
                        current_paper.get('authors', ''), 
                        current_paper.get('abstract', ''), 
                        current_paper.get('doi', ''), 
                        current_paper.get('year', None)
                    ))
                    count += 1
                current_paper = {'authors': []}
            elif tag == 'T1' or tag == 'TI':
                current_paper['title'] = value
            elif tag == 'AU' or tag == 'A1':
                current_paper['authors'].append(value)
            elif tag == 'AB':
                current_paper['abstract'] = value
            elif tag == 'DO':
                current_paper['doi'] = value
            elif tag == 'PY' or tag == 'Y1':
                # Just get the first 4 digits for the year
                year_match = re.search(r'(\d{4})', value)
                if year_match:
                    current_paper['year'] = int(year_match.group(1))

    # Save the last paper
    if current_paper and 'title' in current_paper:
        authors_str = "; ".join(current_paper.get('authors', []))
        cursor.execute('''
            INSERT INTO papers (project_id, title, authors, abstract, doi, year)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (args.project_id, current_paper.get('title', ''), authors_str, current_paper.get('abstract', ''), current_paper.get('doi', ''), current_paper.get('year', None)))
        count += 1
        
    conn.commit()
    conn.close()
    print(f"Successfully imported {count} papers into project {args.project_id}")

def screen(args):
    conn = get_db()
    cursor = conn.cursor()
    
    # Fetch unscreened papers for this project
    cursor.execute('''
        SELECT id, title, authors, year, abstract, doi 
        FROM papers 
        WHERE project_id = ? AND stage = 'unscreened'
    ''', (args.project_id,))
    
    papers = cursor.fetchall()
    if not papers:
        print(f"No unscreened papers found for project {args.project_id}!")
        return

    print(f"Found {len(papers)} unscreened papers. Let's begin screening!\n")
    
    for paper in papers:
        print("-" * 60)
        print(f"[{paper['id']}] Title: {paper['title']}")
        print(f"Authors: {paper['authors']} | Year: {paper['year']}")
        if paper['doi']:
            print(f"DOI: {paper['doi']} (To open later: python prisma.py open-doi {paper['id']})")
        print("\nAbstract:")
        print(paper['abstract'])
        print("-" * 60)
        
        while True:
            choice = input("Include (i) / Exclude (e) / Skip (s) / Quit (q): ").strip().lower()
            if choice == 'i':
                cursor.execute("UPDATE papers SET stage = 'title_included' WHERE id = ?", (paper['id'],))
                conn.commit()
                break
            elif choice == 'e':
                cursor.execute("UPDATE papers SET stage = 'title_excluded' WHERE id = ?", (paper['id'],))
                conn.commit()
                break
            elif choice == 's':
                print("Skipped.")
                break
            elif choice == 'q':
                print("Exiting screening session...")
                conn.close()
                return
            else:
                print("Invalid choice.")
                
    conn.close()
    print("Screening session complete!")

def open_doi(args):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT doi FROM papers WHERE id = ?', (args.paper_id,))
    row = cursor.fetchone()
    
    if not row or not row['doi']:
        print(f"No DOI found for paper ID {args.paper_id}.")
        return
        
    doi = row['doi']
    
    # Clean up DOI just in case
    if doi.startswith("doi:"):
        doi = doi[4:]
    elif doi.startswith("https://doi.org/"):
        doi = doi[16:]
    elif doi.startswith("http://doi.org/"):
        doi = doi[15:]
        
    url = f"https://doi.org/{doi}"
    print(f"Opening {url} in your default browser...")
    webbrowser.open(url)
    
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="PRISMA Pipeline CLI Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # init-db
    subparsers.add_parser('init-db', help="Initialize the SQLite database")
    
    # create-project
    parser_cp = subparsers.add_parser('create-project', help="Create a new systematic review project")
    parser_cp.add_argument("name", help="Name of the project")
    parser_cp.add_argument("--desc", help="Description of the project", default="")
    
    # import-csv
    parser_csv = subparsers.add_parser('import-csv', help="Import papers from a CSV file")
    parser_csv.add_argument("project_id", type=int, help="ID of the project")
    parser_csv.add_argument("file", help="Path to the CSV file")
    
    # import-ris
    parser_ris = subparsers.add_parser('import-ris', help="Import papers from an RIS file")
    parser_ris.add_argument("project_id", type=int, help="ID of the project")
    parser_ris.add_argument("file", help="Path to the RIS file")
    
    # screen
    parser_screen = subparsers.add_parser('screen', help="Start an interactive Title/Abstract screening session")
    parser_screen.add_argument("project_id", type=int, help="ID of the project to screen")
    
    # open-doi
    parser_doi = subparsers.add_parser('open-doi', help="Open the DOI for a specific paper ID in the browser")
    parser_doi.add_argument("paper_id", type=int, help="ID of the paper in the database")
    
    args = parser.parse_args()
    
    if args.command == 'init-db':
        init_db(args)
    elif args.command == 'create-project':
        create_project(args)
    elif args.command == 'import-csv':
        import_csv(args)
    elif args.command == 'import-ris':
        import_ris(args)
    elif args.command == 'screen':
        screen(args)
    elif args.command == 'open-doi':
        open_doi(args)

if __name__ == '__main__':
    main()
