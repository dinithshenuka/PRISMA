"""
menus/extraction_menu.py — Manage extraction schema and run LLM extraction.
"""
from db import add_extraction_column, get_extraction_schema, delete_extraction_column, get_paper_list_by_stage
from menus.utils import clear_screen, pause
from extraction import get_groq_client, extract_text_from_pdf, run_groq_extraction, export_to_csv
import os

def manage_schema_menu(project_id: int):
    while True:
        clear_screen()
        schema = get_extraction_schema(project_id)
        print("=== Manage Extraction Schema ===")
        print("Define the columns you want the LLM to extract from each PDF.\n")
        
        if not schema:
            print("  (No columns defined yet)")
        else:
            for col in schema:
                print(f"  [{col['id']}] {col['column_name']} - {col['description']}")
                
        print("\n  [1] Add new column")
        print("  [2] Delete column")
        print("  [3] Import columns from CSV/JSON file")
        print("  [0] Back")
        
        choice = input("\n  Select option: ").strip()
        if choice == '1':
            name = input("  Column Name (e.g., 'sample_size'): ").strip()
            desc = input("  Description (e.g., 'The number of participants in the study'): ").strip()
            if name and desc:
                add_extraction_column(project_id, name, desc)
        elif choice == '2':
            try:
                col_id = int(input("  Enter Column ID to delete: ").strip())
                delete_extraction_column(col_id)
            except ValueError:
                print("  Invalid ID.")
                pause()
        elif choice == '3':
            file_path = input("  Enter path to CSV or JSON file: ").strip()
            import_schema_from_file(project_id, file_path)
        elif choice == '0':
            break

def import_schema_from_file(project_id: int, file_path: str):
    import csv
    import json
    
    if not os.path.exists(file_path):
        print(f"  [!] File not found: {file_path}")
        pause()
        return

    added = 0
    try:
        if file_path.lower().endswith('.csv'):
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                # Fallback to checking first row if headers don't match
                if reader.fieldnames and 'column_name' not in reader.fieldnames:
                     print("  [!] CSV must have headers: 'column_name', 'description'")
                     pause()
                     return
                for row in reader:
                    name = row.get('column_name', '').strip()
                    desc = row.get('description', '').strip()
                    if name and desc:
                        add_extraction_column(project_id, name, desc)
                        added += 1
        elif file_path.lower().endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        name = item.get('column_name', '').strip()
                        desc = item.get('description', '').strip()
                        if name and desc:
                            add_extraction_column(project_id, name, desc)
                            added += 1
                else:
                    print("  [!] JSON must be a list of objects.")
                    pause()
                    return
        else:
            print("  [!] Unsupported file format. Please use .csv or .json")
            pause()
            return
            
        print(f"  ✅ Successfully imported {added} columns.")
    except Exception as e:
        print(f"  [!] Error reading file: {e}")
    pause()


def run_extraction(project_id: int, project_name: str):
    schema = get_extraction_schema(project_id)
    if not schema:
        print("\n  [!] No extraction schema defined. Please add columns first.")
        pause()
        return
        
    client = get_groq_client()
    if not client:
        print("\n  [!] GROQ_API_KEY environment variable not found or groq package not installed.")
        print("      Export it or add it to a .env file to use this feature.")
        print("      Run: pip install -r requirements.txt")
        pause()
        return
        
    papers = get_paper_list_by_stage(project_id, 'fulltext_retrieved')
    if not papers:
        print("\n  [!] No papers in 'fulltext_retrieved' stage. Nothing to extract.")
        pause()
        return
        
    print(f"\n  Starting extraction for {len(papers)} papers...\n")
    
    extracted_data = []
    
    for idx, p in enumerate(papers, 1):
        pdf_path = p['pdf_path']
        print(f"  [{idx}/{len(papers)}] Processing ID: {p['id']} - {p['title'][:50]}...")
        
        if not pdf_path or not os.path.exists(pdf_path):
            print(f"      [!] PDF not found at {pdf_path}")
            continue
            
        text = extract_text_from_pdf(pdf_path)
        if not text:
            print("      [!] Could not extract text from PDF.")
            continue
            
        print("      Sending to Groq LLM...")
        data = run_groq_extraction(text, schema, client)
        
        if data:
            # Attach base metadata
            row = {
                'paper_id': p['id'],
                'title': p['title'],
                'doi': p['doi']
            }
            row.update(data)
            extracted_data.append(row)
            print("      ✅ Extraction successful.")
        else:
            print("      ❌ Failed to extract data.")
            
    if extracted_data:
        out_csv = export_to_csv(project_name, project_id, schema, extracted_data)
        print(f"\n  🎉 Extraction complete! Saved to:\n  {out_csv}")
    else:
        print("\n  [!] No data was successfully extracted.")
        
    pause()


def extraction_menu(project_id: int, project_name: str):
    while True:
        clear_screen()
        print(f"=== Data Extraction (LLM) | {project_name} ===")
        print("  1. Manage Extraction Schema (Columns)")
        print("  2. Run Extraction on Retrieved PDFs")
        print("  0. Back")
        
        choice = input("\n  Select option: ").strip()
        
        if choice == '1':
            manage_schema_menu(project_id)
        elif choice == '2':
            run_extraction(project_id, project_name)
        elif choice == '0':
            break
