"""acm.py — Importer for ACM Digital Library RIS exports."""

from .base import BaseImporter


class ACMImporter(BaseImporter):
    SOURCE_NAME = "ACM Digital Library"
    FILE_TYPE = "ris"
    # ACM RIS exports have a unique journal tag pattern but we detect by file extension
    SIGNATURE_COLUMNS = set()  # RIS — no CSV columns to check

    def parse(self, filepath: str) -> list[dict]:
        return self.parse_ris(filepath)
