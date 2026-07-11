"""
base.py — Abstract base class for all database-specific importers.
All importers inherit from BaseImporter and implement parse().
"""

import csv
import re
from abc import ABC, abstractmethod


class BaseImporter(ABC):
    """
    Abstract base importer.

    Subclasses must define:
      - SOURCE_NAME: str       — human-readable name of the database
      - FILE_TYPE: str         — 'csv' or 'ris'
      - COLUMN_MAP: dict       — maps internal field names to source column names
      - SIGNATURE_COLUMNS: set — unique columns used for auto-detection

    Subclasses may override:
      - parse(filepath) -> list[dict]
    """

    SOURCE_NAME: str = "Unknown"
    FILE_TYPE: str = "csv"
    COLUMN_MAP: dict = {}
    SIGNATURE_COLUMNS: set = set()

    def _clean_year(self, value: str) -> int | None:
        """Extract a 4-digit year from any date string."""
        if not value:
            return None
        match = re.search(r'(\d{4})', str(value))
        return int(match.group(1)) if match else None

    def _clean_doi(self, value: str) -> str:
        """Strip known DOI prefixes to leave a clean DOI string."""
        doi = str(value).strip()
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
            if doi.startswith(prefix):
                doi = doi[len(prefix):]
        return doi

    def parse_csv(self, filepath: str) -> list[dict]:
        """
        Parse a CSV file using COLUMN_MAP to extract standardised paper dicts.
        """
        papers = []
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper = {}
                for field, col in self.COLUMN_MAP.items():
                    raw = row.get(col, '').strip() if isinstance(col, str) else ''
                    paper[field] = raw

                paper['year'] = self._clean_year(paper.get('year'))
                if paper.get('doi'):
                    paper['doi'] = self._clean_doi(paper['doi'])

                papers.append(paper)
        return papers

    def parse_ris(self, filepath: str) -> list[dict]:
        """
        Generic RIS parser. Subclasses can override for custom tag handling.
        """
        papers = []
        current: dict = {}

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                match = re.match(r'^([A-Z0-9]{2})\s+-\s+(.*)$', line)
                if not match:
                    continue

                tag, value = match.groups()

                if tag == 'TY':
                    if current:
                        papers.append(self._finalise_ris(current))
                    current = {'_authors': []}

                elif tag in ('T1', 'TI'):
                    current['title'] = value
                elif tag in ('AU', 'A1'):
                    current.setdefault('_authors', []).append(value)
                elif tag == 'AB':
                    current['abstract'] = value
                elif tag == 'DO':
                    current['doi'] = self._clean_doi(value)
                elif tag in ('PY', 'Y1'):
                    current['year'] = self._clean_year(value)
                elif tag == 'ER':
                    if current:
                        papers.append(self._finalise_ris(current))
                    current = {}

        if current:
            papers.append(self._finalise_ris(current))

        return [p for p in papers if p.get('title')]

    def _finalise_ris(self, current: dict) -> dict:
        """Convert internal RIS accumulator dict to a standard paper dict."""
        return {
            'title': current.get('title', ''),
            'authors': '; '.join(current.get('_authors', [])),
            'abstract': current.get('abstract', ''),
            'doi': current.get('doi', ''),
            'year': current.get('year'),
        }

    @abstractmethod
    def parse(self, filepath: str) -> list[dict]:
        """Parse the file and return a list of standardised paper dicts."""
        ...
