import streamlit as st
import yaml
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

# Page Config
st.set_page_config(page_title="PrismAI", page_icon="🔍", layout="wide")
st.title("PrismAI: Automated PRISMA Screening")
st.markdown(
    "Easily perform systematic reviews using open databases and local/cloud AI."
)


# Load current config
def load_config():
    with open("config.yaml", "r") as file:
        return yaml.safe_load(file)


def save_config(config):
    with open("config.yaml", "w") as file:
        yaml.dump(config, file, default_flow_style=False)


config = load_config()

# Sidebar
st.sidebar.header("Data Sources")
st.sidebar.markdown(
    "1. The pipeline will automatically fetch from **OpenAlex** and **PubMed**."
)
st.sidebar.markdown(
    "2. To include **Scopus, Embase, IEEE**, or **ACM**, drop your CSV files into the `data/raw` folder."
)
st.sidebar.markdown(
    f"**Current API Key Loaded:** {'✅ Yes' if os.environ.get('GROQ_API_KEY') else '❌ No (.env missing)'}"
)

# Main Configuration Area
st.subheader("1. Project Configuration")

col1, col2 = st.columns(2)
with col1:
    project_name = st.text_input(
        "Project Name", config.get("project_name", "My_Review")
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

if st.button("🚀 Start Screening", type="primary", use_container_width=True):
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
        save_config(config)

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

            status_text.success("✅ Screening Complete!")

            # Show Results
            included_count = len(df_screened[df_screened["ai_decision"] == "INCLUDE"])
            st.metric("Total Papers Included", included_count)

            if included_count > 0:
                included_df = df_screened[df_screened["ai_decision"] == "INCLUDE"]
                st.dataframe(included_df[["title", "doi", "ai_reason"]])

                # Download Button
                csv = included_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download Included Papers (CSV)",
                    data=csv,
                    file_name="included_papers.csv",
                    mime="text/csv",
                )
            else:
                st.warning("No papers met the inclusion criteria.")

        except Exception as e:
            status_text.error(f"An error occurred: {e}")
