import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv

# Load environment variables (gets the API key securely)
load_dotenv()

from src.ingest_apis import run_api_ingestion
from src.ingest_manual import load_manual_files
from src.deduplicate import deduplicate_dataset
from src.screen_llm import screen_papers
from src.report import generate_prisma_report
from src.db import get_project_config, save_project_config

# Page Config
st.set_page_config(page_title="PrismAI", layout="wide")
st.title("PrismAI: Automated PRISMA Screening")
st.markdown("Easily perform systematic reviews using open databases and cloud AI.")

# We can let the user pick a project to load, or default to Default_Project
project_select = st.sidebar.text_input("Project Name to Load/Create", "Default_Project")
config = get_project_config(project_select)

# Sidebar
st.sidebar.header("Data Sources")
st.sidebar.markdown(
    "1. The pipeline will automatically fetch from **OpenAlex** and **PubMed**."
)
st.sidebar.markdown(
    "2. To include **Scopus, Embase, IEEE**, or **ACM**, drop your CSV files into the `data/raw` folder."
)
st.sidebar.markdown(
    f"**Current API Key Loaded:** {'Yes' if os.environ.get('GROQ_API_KEY') else 'No (.env missing)'}"
)

# Main Configuration Area
st.subheader("1. Project Configuration")

col1, col2 = st.columns(2)
with col1:
    project_name = st.text_input(
        "Project Name", config.get("project_name", "Default_Project")
    )
    llm_model = st.text_input(
        "LLM Model (Groq)", config.get("llm_model", "llama-3.1-8b-instant")
    )
    max_results = int(
        st.number_input(
            "Max Papers to Fetch (per database)",
            min_value=1,
            max_value=1000,
            value=config.get("max_results", 10),
        )
    )

with col2:
    st.markdown("**Search Queries**")
    query_openalex = st.text_input(
        "OpenAlex Query", config["search_queries"].get("openalex", "")
    )
    query_pubmed = st.text_input(
        "PubMed Query", config["search_queries"].get("pubmed", "")
    )

st.subheader("2. Screening Criteria")
st.info("The AI will strictly follow these rules to include or exclude papers.")

col3, col4 = st.columns(2)
with col3:
    inc_text = st.text_area(
        "Inclusion Criteria (One per line)",
        "\n".join(config.get("inclusion_criteria", [])),
        height=150,
    )
with col4:
    exc_text = st.text_area(
        "Exclusion Criteria (One per line)",
        "\n".join(config.get("exclusion_criteria", [])),
        height=150,
    )

# Run Pipeline
st.divider()
st.subheader("3. Run Pipeline")

if st.button("Start Screening", type="primary", use_container_width=True):
    if not os.environ.get("GROQ_API_KEY"):
        st.error("Missing GROQ_API_KEY in .env file! Please add it before running.")
    else:
        # Save updated config
        config["project_name"] = project_name
        config["llm_model"] = llm_model
        config["max_results"] = max_results
        config["search_queries"]["openalex"] = query_openalex
        config["search_queries"]["pubmed"] = query_pubmed
        config["inclusion_criteria"] = [
            x.strip() for x in inc_text.split("\n") if x.strip()
        ]
        config["exclusion_criteria"] = [
            x.strip() for x in exc_text.split("\n") if x.strip()
        ]
        save_project_config(config)

        # UI Status Updates
        status_text = st.empty()
        progress_bar = st.progress(0)

        try:
            status_text.info("Phase 1: Fetching papers from databases...")
            df_api = run_api_ingestion(config)
            df_manual = load_manual_files()
            df_combined = pd.concat([df_api, df_manual], ignore_index=True)
            initial_counts = {
                "api": len(df_api),
                "manual": len(df_manual),
                "total": len(df_combined),
            }
            progress_bar.progress(25)

            status_text.info("Phase 2: Removing duplicates...")
            df_clean = deduplicate_dataset(df_combined)
            duplicates_removed = len(df_combined) - len(df_clean)
            progress_bar.progress(50)

            status_text.info(
                f"Phase 3: AI Screening {len(df_clean)} papers using {llm_model}... (This may take a minute)"
            )
            df_screened = screen_papers(df_clean, config)
            progress_bar.progress(90)

            status_text.info("Phase 4: Generating Report...")
            generate_prisma_report(df_screened, initial_counts, duplicates_removed)
            progress_bar.progress(100)

            status_text.success("Screening Complete!")

            # Show Results
            included_count = len(df_screened[df_screened["ai_decision"] == "INCLUDE"])
            notsure_count = len(df_screened[df_screened["ai_decision"] == "NOT SURE"])
            
            st.subheader("Screening Results")
            st.metric("Total Papers Included", included_count)
            st.metric("Papers Marked 'NOT SURE'", notsure_count)
            
            # Show full interactive table with all decisions
            st.markdown("### All Screened Papers")
            st.dataframe(df_screened[["title", "doi", "ai_decision", "ai_reason"]])
            
            csv_all = df_screened.to_csv(index=False).encode("utf-8")
            st.download_button("Download Full Results (CSV)", data=csv_all, file_name="all_screened_papers.csv", mime="text/csv")
            
            if included_count > 0:
                included_df = df_screened[df_screened["ai_decision"] == "INCLUDE"]
                csv_inc = included_df.to_csv(index=False).encode("utf-8")
                st.download_button("Download ONLY Included Papers", data=csv_inc, file_name="included_papers.csv", mime="text/csv")
                
            if notsure_count > 0:
                notsure_df = df_screened[df_screened["ai_decision"] == "NOT SURE"]
                csv_not = notsure_df.to_csv(index=False).encode("utf-8")
                st.download_button("Download ONLY 'Not Sure' Papers", data=csv_not, file_name="notsure_papers.csv", mime="text/csv")

            if os.path.exists("data/processed/prisma_flowchart.png"):
                st.image(
                    "data/processed/prisma_flowchart.png", caption="PRISMA Flow Diagram"
                )

        except Exception as e:
            status_text.error(f"An error occurred: {e}")
