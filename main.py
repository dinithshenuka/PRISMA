import yaml
from src.ingest_apis import run_api_ingestion
from src.ingest_manual import load_manual_files
from src.deduplicate import deduplicate_dataset
from src.screen_llm import screen_papers
from src.report import generate_prisma_report
import pandas as pd
import warnings

warnings.filterwarnings("ignore")


def load_config(config_path="config.yaml"):
    with open(config_path, "r") as file:
        return yaml.safe_load(file)


def main():
    print("=== Starting PrismAI Pipeline ===")
    config = load_config()
    print(f"Project: {config.get('project_name')}")

    # 1. Ingestion Phase
    print("\n--- PHASE 1: IDENTIFICATION ---")
    df_api = run_api_ingestion(config)
    df_manual = load_manual_files()

    df_combined = pd.concat([df_api, df_manual], ignore_index=True)
    initial_counts = {
        "api": len(df_api),
        "manual": len(df_manual),
        "total": len(df_combined),
    }

    # 2. Deduplication Phase
    print("\n--- PHASE 2: DEDUPLICATION ---")
    df_clean = deduplicate_dataset(df_combined)
    duplicates_removed = len(df_combined) - len(df_clean)

    # 3. Screening Phase
    print("\n--- PHASE 3: AI SCREENING ---")
    df_screened = screen_papers(df_clean, config)

    # 4. Reporting Phase
    print("\n--- PHASE 4: PRISMA REPORTING ---")
    generate_prisma_report(df_screened, initial_counts, duplicates_removed)
    print("\n=== PrismAI Pipeline Complete ===")


if __name__ == "__main__":
    main()
