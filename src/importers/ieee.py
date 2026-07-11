"""ieee.py — Importer for IEEE Xplore CSV exports."""

from .base import BaseImporter


class IEEEImporter(BaseImporter):
    SOURCE_NAME = "IEEE Xplore"
    FILE_TYPE = "csv"
    SIGNATURE_COLUMNS = {"Document Title", "Publication Title", "IEEE Terms"}
    COLUMN_MAP = {
        "title":    "Document Title",
        "authors":  "Authors",
        "abstract": "Abstract",
        "doi":      "DOI",
        "year":     "Publication Year",
    }

    def parse(self, filepath: str) -> list[dict]:
        return self.parse_csv(filepath)
