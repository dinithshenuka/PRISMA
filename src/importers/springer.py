"""springer.py — Importer for SpringerLink CSV exports."""

from .base import BaseImporter


class SpringerImporter(BaseImporter):
    SOURCE_NAME = "SpringerLink"
    FILE_TYPE = "csv"
    SIGNATURE_COLUMNS = {"Item Title", "Item DOI", "Publication Title"}
    COLUMN_MAP = {
        "title":    "Item Title",
        "authors":  "Authors",
        "abstract": "Abstract",
        "doi":      "Item DOI",
        "year":     "Publication Year",
    }

    def parse(self, filepath: str) -> list[dict]:
        return self.parse_csv(filepath)
