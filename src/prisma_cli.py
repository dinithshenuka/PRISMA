#!/usr/bin/env python3
import sqlite3
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

def init_db():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
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

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_project_dir(project_id, project_name):
    # Sanitize project name to be safe for folder names
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', project_name).strip('_').lower()
    if not safe_name:
        safe_name = "project"
    return os.path.join(BASE_DIR, 'data', 'imports', f"{safe_name}_{project_id}")

# --- Backend Operations ---

def create_project(name, desc):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO projects (name, description) VALUES (?, ?)", (name, desc))
    project_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    project_dir = get_project_dir(project_id, name)
    os.makedirs(project_dir, exist_ok=True)
    return project_id

def import_csv(project_id, filepath):
    if not os.path.exists(filepath):
        print(f"\n[!] File not found: {filepath}")
        return
        
    conn = get_db()
    cursor = conn.cursor()
    count = 0
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
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
                ''', (project_id, title, authors, abstract, doi, year))
                count += 1
        conn.commit()
        print(f"\n[+] Successfully imported {count} papers!")
    except Exception as e:
        print(f"\n[!] Error importing CSV: {e}")
    finally:
        conn.close()

def import_ris(project_id, filepath):
    if not os.path.exists(filepath):
        print(f"\n[!] File not found: {filepath}")
        return
        
    conn = get_db()
    cursor = conn.cursor()
    count = 0
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        current_paper = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            match = re.match(r'^([A-Z0-9]{2})\s+-\s+(.*)$', line)
            if match:
                tag, value = match.groups()
                
                if tag == 'TY':
                    if current_paper:
                        cursor.execute('''
                            INSERT INTO papers (project_id, title, authors, abstract, doi, year)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            project_id, 
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
                    year_match = re.search(r'(\d{4})', value)
                    if year_match:
                        current_paper['year'] = int(year_match.group(1))

        if current_paper and 'title' in current_paper:
            authors_str = "; ".join(current_paper.get('authors', []))
            cursor.execute('''
                INSERT INTO papers (project_id, title, authors, abstract, doi, year)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (project_id, current_paper.get('title', ''), authors_str, current_paper.get('abstract', ''), current_paper.get('doi', ''), current_paper.get('year', None)))
            count += 1
            
        conn.commit()
        print(f"\n[+] Successfully imported {count} papers!")
    except Exception as e:
        print(f"\n[!] Error importing RIS: {e}")
    finally:
        conn.close()

def screen_project(project_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, title, authors, year, abstract, doi 
        FROM papers 
        WHERE project_id = ? AND stage = 'unscreened'
    ''', (project_id,))
    
    papers = cursor.fetchall()
    if not papers:
        print("\n[!] No unscreened papers found for this project!")
        conn.close()
        input("\nPress Enter to continue...")
        return

    clear_screen()
    print(f"Found {len(papers)} unscreened papers. Let's begin screening!\n")
    
    for paper in papers:
        print("=" * 80)
        print(f"[{paper['id']}] TITLE: {paper['title']}")
        print(f"AUTHORS: {paper['authors']}")
        print(f"YEAR: {paper['year']}  |  DOI: {paper['doi']}")
        print("-" * 80)
        print("ABSTRACT:")
        print(paper['abstract'])
        print("=" * 80)
        
        while True:
            print("\nOptions: (i) Include | (e) Exclude | (o) Open DOI in Browser | (s) Skip | (q) Quit")
            choice = input("Your choice: ").strip().lower()
            
            if choice == 'i':
                cursor.execute("UPDATE papers SET stage = 'title_included' WHERE id = ?", (paper['id'],))
                conn.commit()
                break
            elif choice == 'e':
                cursor.execute("UPDATE papers SET stage = 'title_excluded' WHERE id = ?", (paper['id'],))
                conn.commit()
                break
            elif choice == 'o':
                if paper['doi']:
                    open_doi(paper['id'])
                else:
                    print("No DOI available for this paper.")
            elif choice == 's':
                print("Skipped.")
                break
            elif choice == 'q':
                print("Saving progress and exiting screening session...")
                conn.close()
                return
            else:
                print("Invalid choice.")
        
        clear_screen()
                
    conn.close()
    print("\n[+] Screening session complete! No more unscreened papers.")
    input("\nPress Enter to return to menu...")

def open_doi(paper_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT doi FROM papers WHERE id = ?', (paper_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row['doi']:
        print(f"No DOI found for paper ID {paper_id}.")
        return
        
    doi = row['doi']
    if doi.startswith("doi:"): doi = doi[4:]
    elif doi.startswith("https://doi.org/"): doi = doi[16:]
    elif doi.startswith("http://doi.org/"): doi = doi[15:]
        
    url = f"https://doi.org/{doi}"
    print(f"Opening {url} in browser...")
    webbrowser.open(url)

# --- UI Menus ---

def project_menu(project_id, project_name):
    while True:
        clear_screen()
        print(f"=== PRISMA Pipeline | Project: {project_name} ===")
        print("1. Import papers from .csv")
        print("2. Import papers from .ris")
        print("3. Start Title/Abstract Screening")
        print("4. Open a specific paper DOI")
        print("5. Back to Main Menu")
        print("===================================")
        
        choice = input("Select an option (1-5): ").strip()
        
        if choice == '1':
            project_dir = get_project_dir(project_id, project_name)
            os.makedirs(project_dir, exist_ok=True)
            files = [f for f in os.listdir(project_dir) if f.lower().endswith('.csv')]
            
            if not files:
                print(f"\n[!] No .csv files found in {project_dir}/")
                input("\nPress Enter to continue...")
                continue
                
            print(f"\nFound .csv files in {project_dir}/ :")
            for i, f in enumerate(files, 1):
                print(f"[{i}] {f}")
            print("[0] Cancel")
            
            try:
                f_idx = int(input("\nSelect a file to import: "))
                if f_idx == 0:
                    continue
                if 1 <= f_idx <= len(files):
                    import_csv(project_id, os.path.join(project_dir, files[f_idx-1]))
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Invalid input.")
            input("\nPress Enter to continue...")
            
        elif choice == '2':
            project_dir = get_project_dir(project_id, project_name)
            os.makedirs(project_dir, exist_ok=True)
            files = [f for f in os.listdir(project_dir) if f.lower().endswith('.ris')]
            
            if not files:
                print(f"\n[!] No .ris files found in {project_dir}/")
                input("\nPress Enter to continue...")
                continue
                
            print(f"\nFound .ris files in {project_dir}/ :")
            for i, f in enumerate(files, 1):
                print(f"[{i}] {f}")
            print("[0] Cancel")
            
            try:
                f_idx = int(input("\nSelect a file to import: "))
                if f_idx == 0:
                    continue
                if 1 <= f_idx <= len(files):
                    import_ris(project_id, os.path.join(project_dir, files[f_idx-1]))
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Invalid input.")
            input("\nPress Enter to continue...")
            
        elif choice == '3':
            screen_project(project_id)
            
        elif choice == '4':
            try:
                pid = int(input("\nEnter the Database ID of the paper: "))
                open_doi(pid)
            except ValueError:
                print("Invalid ID.")
            input("\nPress Enter to continue...")
            
        elif choice == '5':
            break

def main_menu():
    init_db()
    
    while True:
        clear_screen()
        print("=== PRISMA Pipeline Manager ===")
        print("1. Open an existing project")
        print("2. Create a new project")
        print("3. Exit")
        print("===============================")
        
        choice = input("Select an option (1-3): ").strip()
        
        if choice == '1':
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM projects ORDER BY created_at DESC")
            projects = cursor.fetchall()
            conn.close()
            
            if not projects:
                print("\n[!] No projects found. Please create one first.")
                input("\nPress Enter to continue...")
                continue
                
            print("\n--- Existing Projects ---")
            for p in projects:
                print(f"[{p['id']}] {p['name']}")
                
            print("[0] Cancel")
            
            try:
                pid = int(input("\nEnter Project ID to open: "))
                if pid == 0:
                    continue
                selected = next((p for p in projects if p['id'] == pid), None)
                if selected:
                    project_menu(selected['id'], selected['name'])
                else:
                    print("Invalid Project ID.")
                    input("\nPress Enter to continue...")
            except ValueError:
                print("Invalid input.")
                input("\nPress Enter to continue...")
                
        elif choice == '2':
            print("\n--- Create New Project ---")
            name = input("Project Name: ").strip()
            if not name:
                print("Name cannot be empty.")
                input("\nPress Enter to continue...")
                continue
            desc = input("Description (optional): ").strip()
            
            pid = create_project(name, desc)
            pdir = get_project_dir(pid, name)
            print(f"\n[+] Project created successfully! ID: {pid}")
            print(f"[+] Import folder created: {pdir}/")
            input("\nPress Enter to open this project...")
            project_menu(pid, name)
            
        elif choice == '3':
            clear_screen()
            print("Exiting PRISMA Pipeline Manager. Goodbye!")
            sys.exit(0)

if __name__ == '__main__':
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
