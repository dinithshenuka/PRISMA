"""pubmed.py — Importer for PubMed CSV exports."""

from .base import BaseImporter


class PubMedImporter(BaseImporter):
    SOURCE_NAME = "PubMed"
    FILE_TYPE = "csv"
    SIGNATURE_COLUMNS = {"PMID", "NIHMS ID", "PMC ID"}
    COLUMN_MAP = {
        "title":    "Title",
        "authors":  "Authors",
        "abstract": "Abstract",
        "doi":      "DOI",
        "year":     "Publication Year",
    }

    def parse(self, filepath: str) -> list[dict]:
        return self.parse_csv(filepath)
