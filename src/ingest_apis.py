import requests
import pandas as pd
import xml.etree.ElementTree as ET
import time


def fetch_openalex(query, max_results=100):
    print(f"Fetching from OpenAlex with query: {query}")
    url = f"https://api.openalex.org/works?search={query}&per-page=50"
    papers = []

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        for item in data.get("results", [])[:max_results]:
            title = item.get("title")

            # Abstract comes inverted in OpenAlex, we need to reconstruct it
            abstract_inverted = item.get("abstract_inverted_index", {})
            abstract = ""
            if abstract_inverted:
                # Reconstruct abstract
                word_index = []
                for word, positions in abstract_inverted.items():
                    for pos in positions:
                        word_index.append((pos, word))
                word_index.sort()
                abstract = " ".join([word for pos, word in word_index])

            doi = (
                item.get("doi", "").replace("https://doi.org/", "")
                if item.get("doi")
                else ""
            )
            year = item.get("publication_year", "")

            if title and abstract:
                papers.append(
                    {
                        "title": title,
                        "abstract": abstract,
                        "doi": doi,
                        "year": year,
                        "source": "OpenAlex",
                    }
                )
        print(f"Found {len(papers)} papers from OpenAlex.")
    except Exception as e:
        print(f"Error fetching from OpenAlex: {e}")

    return pd.DataFrame(papers)


def fetch_pubmed(query, max_results=100):
    print(f"Fetching from PubMed with query: {query}")
    email = "example@example.com"
    papers = []

    try:
        # Step 1: ESearch
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={requests.utils.quote(query)}&retmax={max_results}&retmode=json&email={email}"
        response = requests.get(search_url)
        response.raise_for_status()
        search_data = response.json()

        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            print("No papers found in PubMed.")
            return pd.DataFrame(papers)

        # Step 2: EFetch
        ids_str = ",".join(id_list)
        fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={ids_str}&retmode=xml&email={email}"
        fetch_resp = requests.get(fetch_url)
        fetch_resp.raise_for_status()

        # Parse XML
        root = ET.fromstring(fetch_resp.content)

        for article in root.findall(".//PubmedArticle"):
            title = ""
            title_node = article.find(".//ArticleTitle")
            if title_node is not None and title_node.text:
                title = title_node.text

            abstract = ""
            abstract_texts = article.findall(".//AbstractText")
            if abstract_texts:
                abstract = " ".join([node.text for node in abstract_texts if node.text])

            doi = ""
            for el in article.findall(".//ArticleId"):
                if el.get("IdType") == "doi" and el.text:
                    doi = el.text
                    break

            year = ""
            year_node = article.find(".//PubDate/Year")
            if year_node is not None and year_node.text:
                year = year_node.text

            if title and abstract:
                papers.append(
                    {
                        "title": title,
                        "abstract": abstract,
                        "doi": doi,
                        "year": year,
                        "source": "PubMed",
                    }
                )
        print(f"Found {len(papers)} papers from PubMed.")
    except Exception as e:
        print(f"Error fetching from PubMed: {e}")

    return pd.DataFrame(papers)


def run_api_ingestion(config):
    df_openalex = pd.DataFrame()
    df_pubmed = pd.DataFrame()

    max_results = config.get("max_results", 100)

    if "openalex" in config["search_queries"]:
        df_openalex = fetch_openalex(
            config["search_queries"]["openalex"], max_results=max_results
        )

    if "pubmed" in config["search_queries"]:
        df_pubmed = fetch_pubmed(
            config["search_queries"]["pubmed"], max_results=max_results
        )

    df_combined = pd.concat([df_openalex, df_pubmed], ignore_index=True)
    return df_combined
