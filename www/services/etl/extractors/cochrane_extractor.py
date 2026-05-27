"""Cochrane Library citation export extractor."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..exceptions import ExtractionError
from .base import BaseExtractor


class CochraneFileExtractor(BaseExtractor):
    """Parse Cochrane Library plain-text citation export files.

    Each record begins with ``Record #N of M`` and uses ``KEY: value``
    lines where multi-valued fields (AU, KW) are repeated.
    """

    # Mapping from Cochrane tag → raw column name in the produced DataFrame
    TAG_TO_COLUMN = {
        "ID": "ID",
        "AU": "Authors",
        "TI": "Title",
        "SO": "Source",
        "YR": "Year",
        "VL": "Volume",
        "IS": "Issue",
        "PG": "Pages",
        "DOI": "DOI",
        "PT": "Publication Type",
        "AB": "Abstract",
        "KW": "Keywords",
        "DE": "Keywords",
        "LA": "Language",
    }

    MULTI_VALUE_TAGS = {"AU", "KW", "DE"}

    def __init__(self, input_path: str):
        self.input_path = Path(input_path)

    def extract(self) -> pd.DataFrame:
        if not self.input_path.exists():
            raise ExtractionError(f"Cochrane file not found: {self.input_path}")
        try:
            text = self.input_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            raise ExtractionError(f"Failed to read {self.input_path}: {exc}") from exc

        records: list[dict[str, object]] = []
        current: dict[str, object] = {}
        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            if line.startswith("Record #"):
                if current:
                    records.append(self._finalize(current))
                    current = {}
                continue
            if not line or ":" not in line:
                continue
            tag, _, value = line.partition(":")
            tag = tag.strip().upper()
            value = value.strip()
            if not value:
                continue
            col = self.TAG_TO_COLUMN.get(tag)
            if not col:
                continue
            if tag in self.MULTI_VALUE_TAGS:
                current.setdefault(col, []).append(value)
            else:
                current[col] = value

        if current:
            records.append(self._finalize(current))

        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records)

    @staticmethod
    def _finalize(record: dict[str, object]) -> dict[str, object]:
        """Normalize list-valued multi-occurrence fields."""
        out: dict[str, object] = {}
        for key, value in record.items():
            if isinstance(value, list):
                out[key] = "; ".join(str(v) for v in value)
            else:
                out[key] = value
        return out
