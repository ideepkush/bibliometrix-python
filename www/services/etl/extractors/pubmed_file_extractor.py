"""Simple PubMed MEDLINE-style TXT extractor."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..exceptions import ExtractionError
from .base import BaseExtractor


class PubMedFileExtractor(BaseExtractor):
    """Read PubMed TXT files in a MEDLINE-like tagged format."""

    TAG_MAP = {
        "PMID": "PMID",
        "TI": "Title",
        "JT": "Journal",
        "TA": "Journal",
        "DP": "Year",
        "PT": "Publication Type",
        "LA": "Language",
        "AID": "DOI",
        "AU": "Authors",
        "FAU": "Author Full Names",
        "AD": "Affiliations",
        "OT": "Keywords",
        "MH": "MeSH Terms",
        "AB": "Abstract",
        "VI": "Volume",
        "IP": "Issue",
        "PG": "Medline Page",
    }

    MULTI_FIELDS = {
        "Authors",
        "Author Full Names",
        "Affiliations",
        "Keywords",
        "MeSH Terms",
        "Publication Type",
    }

    def __init__(self, input_path: str):
        self.input_path = Path(input_path)

    def extract(self) -> pd.DataFrame:
        """Parse PubMed records into a raw DataFrame."""
        if not self.input_path.exists():
            raise ExtractionError(f"PubMed file not found: {self.input_path}")
        try:
            text = self.input_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = self.input_path.read_text(encoding="latin-1")
        except Exception as exc:
            raise ExtractionError(f"Failed to read PubMed TXT: {exc}") from exc

        records = [record for record in text.split("\n\n") if record.strip()]
        parsed = [self._parse_record(record) for record in records]
        return pd.DataFrame(parsed)

    def _parse_record(self, record: str) -> dict[str, object]:
        parsed: dict[str, object] = {}
        current_field = None

        for line in record.splitlines():
            if not line.strip():
                continue
            if len(line) > 6 and line[4:6] == "- ":
                tag = line[:4].strip()
                value = line[6:].strip()
                field = self.TAG_MAP.get(tag)
                current_field = field
                if not field:
                    continue
                self._append_value(parsed, field, value)
            elif current_field:
                continuation = line.strip()
                if continuation:
                    self._append_value(parsed, current_field, continuation, continuation=True)

        doi = parsed.get("DOI")
        if isinstance(doi, list):
            doi_values = [item for item in doi if "[doi]" in item.lower()]
            parsed["DOI"] = doi_values[0].replace("[doi]", "").strip() if doi_values else ""
        elif isinstance(doi, str) and "[doi]" in doi.lower():
            parsed["DOI"] = doi.replace("[doi]", "").strip()

        return parsed

    def _append_value(
        self,
        parsed: dict[str, object],
        field: str,
        value: str,
        continuation: bool = False,
    ) -> None:
        if field in self.MULTI_FIELDS:
            parsed.setdefault(field, [])
            assert isinstance(parsed[field], list)
            if continuation and parsed[field]:
                parsed[field][-1] = f"{parsed[field][-1]} {value}"
            else:
                parsed[field].append(value)
            return

        if continuation and field in parsed:
            parsed[field] = f"{parsed[field]} {value}"
        else:
            parsed[field] = value

