import os
import json
import csv
import time
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_groq_client():
    try:
        from groq import Groq
    except ImportError:
        return None
        
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Reads all text from a PDF file using pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        print("[!] pypdf is not installed. Please run: pip install -r requirements.txt")
        return ""
        
    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    except Exception as e:
        print(f"  [!] Error reading PDF {pdf_path}: {e}")
    return text


def run_groq_extraction(text: str, schema: list, client) -> dict:
    """
    Given the full text of a paper and the extraction schema,
    prompts the Groq LLM to extract data strictly based on the schema
    and return it as a JSON object.
    """
    # Construct the JSON schema required for Groq's output
    json_schema = {}
    for col in schema:
        col_name = col['column_name']
        json_schema[col_name] = {
            "type": "string",
            "description": col['description'] + ' (If not found, strictly output "Not stated")'
        }
    
    system_prompt = (
        "You are an expert academic data extractor. "
        "Read the provided academic paper text carefully. "
        "Extract the requested fields based on the schema provided. "
        "CRITICAL RULES:\n"
        "1. DO NOT guess or hallucinate. If the information is not explicitly stated in the text, you MUST output 'Not stated' for that field.\n"
        "2. You MUST return ONLY a valid JSON object. No preamble, no markdown formatting.\n"
        "3. The keys of the JSON object must match the schema exactly."
    )
    
    # Truncate text to prevent Error 413 (Request too large for 6000 TPM limit on free tier)
    max_chars = 12000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n...[TEXT TRUNCATED DUE TO TOKEN LIMITS]..."

    schema_str = json.dumps(json_schema, indent=2)
    user_prompt = f"Schema:\n{schema_str}\n\nPaper Text (may be long):\n{text}"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            
            output = completion.choices[0].message.content
            return json.loads(output)
        except Exception as e:
            err_str = str(e)
            if "rate_limit_exceeded" in err_str or "429" in err_str:
                print(f"\n      [!] API rate limit hit. Sleeping for 60 seconds... (Attempt {attempt+1}/{max_retries})")
                time.sleep(60)
            elif "json_validate_failed" in err_str or "max completion tokens" in err_str:
                print(f"\n      [!] Incomplete JSON output from model. Retrying... (Attempt {attempt+1}/{max_retries})")
                time.sleep(5)
            else:
                print(f"\n      [!] LLM Extraction Error: {e}")
                return {}
                
    print("\n      [!] Max retries reached for this paper.")
    return {}


def export_to_csv(project_name: str, project_id: int, schema: list, data_rows: list[dict]) -> str:
    """
    Appends or creates a CSV file with the extracted data.
    """
    safe_name = "".join(c if c.isalnum() else "_" for c in project_name).strip("_").lower()
    if not safe_name: 
        safe_name = "project"
    
    out_dir = os.path.join(BASE_DIR, 'data', 'extractions', f"{safe_name}_{project_id}")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "extractions.csv")
    
    fieldnames = ['paper_id', 'title', 'doi'] + [col['column_name'] for col in schema]
    
    file_exists = os.path.isfile(out_file)
    
    with open(out_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        if not file_exists:
            writer.writeheader()
        
        for row in data_rows:
            writer.writerow(row)
            
    return out_file
