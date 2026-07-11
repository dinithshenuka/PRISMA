"""scopus.py — Importer for Scopus CSV exports."""

from .base import BaseImporter


class ScopusImporter(BaseImporter):
    SOURCE_NAME = "Scopus"
    FILE_TYPE = "csv"
    SIGNATURE_COLUMNS = {"EID", "Source title", "CODEN"}
    COLUMN_MAP = {
        "title":    "Title",
        "authors":  "Authors",
        "abstract": "Abstract",
        "doi":      "DOI",
        "year":     "Year",
    }

    def parse(self, filepath: str) -> list[dict]:
        return self.parse_csv(filepath)
