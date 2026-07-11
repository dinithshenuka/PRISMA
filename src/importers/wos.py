"""wos.py — Importer for Web of Science CSV exports."""

from .base import BaseImporter


class WoSImporter(BaseImporter):
    SOURCE_NAME = "Web of Science"
    FILE_TYPE = "csv"
    SIGNATURE_COLUMNS = {"Article Title", "Author Full Names", "Web of Science Core Collection"}
    COLUMN_MAP = {
        "title":    "Article Title",
        "authors":  "Author Full Names",
        "abstract": "Abstract",
        "doi":      "DOI",
        "year":     "Publication Year",
    }

    def parse(self, filepath: str) -> list[dict]:
        return self.parse_csv(filepath)
