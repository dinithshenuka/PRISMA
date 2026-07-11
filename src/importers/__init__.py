"""
importers/__init__.py — Auto-detection logic for database importers.

Peeks at the headers of a CSV/RIS file and returns the correct importer
instance without requiring manual selection by the user.
"""

import csv
from pathlib import Path

from .ieee import IEEEImporter
from .pubmed import PubMedImporter
from .scopus import ScopusImporter
from .wos import WoSImporter
from .acm import ACMImporter
from .springer import SpringerImporter
from .base import BaseImporter

# All CSV importers, ordered by specificity (most unique signatures first)
CSV_IMPORTERS: list[type[BaseImporter]] = [
    IEEEImporter,
    ScopusImporter,
    WoSImporter,
    SpringerImporter,
    PubMedImporter,
]

# RIS importers (detected by file extension only for now)
RIS_IMPORTERS: list[type[BaseImporter]] = [
    ACMImporter,
]


def _get_csv_headers(filepath: str) -> set[str]:
    """Read just the header row of a CSV and return as a set of column names."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        headers = next(reader, [])
    return set(h.strip() for h in headers)


def detect_importer(filepath: str) -> BaseImporter:
    """
    Auto-detect the correct importer for a given file.

    Detection strategy:
    - RIS files (.ris) → use ACMImporter (generic RIS parser)
    - CSV files (.csv) → check each importer's SIGNATURE_COLUMNS against
      the file's actual headers. First match wins.
    - Unknown → fall back to a generic CSV import attempt with PubMed mappings.
    """
    ext = Path(filepath).suffix.lower()

    if ext == '.ris':
        return ACMImporter()

    if ext == '.csv':
        headers = _get_csv_headers(filepath)
        for ImporterClass in CSV_IMPORTERS:
            if ImporterClass.SIGNATURE_COLUMNS and \
               ImporterClass.SIGNATURE_COLUMNS.issubset(headers):
                return ImporterClass()

        # Fallback: return PubMed importer as a generic CSV parser
        return PubMedImporter()

    raise ValueError(f"Unsupported file type: {ext}. Only .csv and .ris are supported.")


__all__ = [
    "detect_importer",
    "IEEEImporter",
    "PubMedImporter",
    "ScopusImporter",
    "WoSImporter",
    "ACMImporter",
    "SpringerImporter",
]
