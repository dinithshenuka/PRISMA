import requests
import pandas as pd
from Bio import Entrez
import time

def fetch_openalex(query, max_results=100):
    print(f"Fetching from OpenAlex with query: {query}")
    url = f"https://api.openalex.org/works?search={query}&per-page=50"
    papers = []
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        for item in data.get('results', [])[:max_results]:
            title = item.get('title')
            
            # Abstract comes inverted in OpenAlex, we need to reconstruct it
            abstract_inverted = item.get('abstract_inverted_index', {})
            abstract = ""
            if abstract_inverted:
                # Reconstruct abstract
                word_index = []
                for word, positions in abstract_inverted.items():
                    for pos in positions:
                        word_index.append((pos, word))
                word_index.sort()
                abstract = " ".join([word for pos, word in word_index])
                
            doi = item.get('doi', '').replace('https://doi.org/', '') if item.get('doi') else ''
            year = item.get('publication_year', '')
            
            if title and abstract:
                papers.append({
                    'title': title,
                    'abstract': abstract,
                    'doi': doi,
                    'year': year,
                    'source': 'OpenAlex'
                })
        print(f"Found {len(papers)} papers from OpenAlex.")
    except Exception as e:
        print(f"Error fetching from OpenAlex: {e}")
        
    return pd.DataFrame(papers)

def fetch_pubmed(query, max_results=100):
    print(f"Fetching from PubMed with query: {query}")
    Entrez.email = "example@example.com"  # Always provide an email to NCBI
    papers = []
    
    try:
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
        record = Entrez.read(handle)
        handle.close()
        
        id_list = record["IdList"]
        if not id_list:
            print("No papers found in PubMed.")
            return pd.DataFrame(papers)
            
        handle = Entrez.efetch(db="pubmed", id=id_list, retmode="xml")
        records = Entrez.read(handle)
        handle.close()
        
        for article in records.get("PubmedArticle", []):
            medline_citation = article.get("MedlineCitation", {})
            article_data = medline_citation.get("Article", {})
            
            title = article_data.get("ArticleTitle", "")
            
            abstract_texts = article_data.get("Abstract", {}).get("AbstractText", [])
            abstract = " ".join([str(text) for text in abstract_texts]) if abstract_texts else ""
            
            doi = ""
            for el in article.get("PubmedData", {}).get("ArticleIdList", []):
                if el.attributes.get("IdType") == "doi":
                    doi = str(el)
                    break
                    
            year = ""
            try:
                year = article_data.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {}).get("Year", "")
            except:
                pass
                
            if title and abstract:
                papers.append({
                    'title': title,
                    'abstract': abstract,
                    'doi': doi,
                    'year': year,
                    'source': 'PubMed'
                })
        print(f"Found {len(papers)} papers from PubMed.")
    except Exception as e:
        print(f"Error fetching from PubMed: {e}")
        
    return pd.DataFrame(papers)

def run_api_ingestion(config):
    df_openalex = pd.DataFrame()
    df_pubmed = pd.DataFrame()
    
    if 'openalex' in config['search_queries']:
        df_openalex = fetch_openalex(config['search_queries']['openalex'])
        
    if 'pubmed' in config['search_queries']:
        df_pubmed = fetch_pubmed(config['search_queries']['pubmed'])
        
    df_combined = pd.concat([df_openalex, df_pubmed], ignore_index=True)
    return df_combined
