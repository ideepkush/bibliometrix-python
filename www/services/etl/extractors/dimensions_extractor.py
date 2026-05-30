"""Dimensions Excel extractor."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..exceptions import ExtractionError
from .base import BaseExtractor


class DimensionsExcelExtractor(BaseExtractor):
    """Read manually exported Dimensions XLSX files."""

    def __init__(self, input_path: str):
        self.input_path = Path(input_path)

    def extract(self) -> pd.DataFrame:
        """Return raw Dimensions records as a DataFrame."""
        if not self.input_path.exists():
            raise ExtractionError(f"Dimensions file not found: {self.input_path}")
        try:
            # Dimensions exports prepend a one-line copyright / "About the data"
            # banner before the real header row, so the actual column names
            # (Title, Authors, Publication Year, ...) live on the second row.
            # Skip that banner; otherwise every column maps to empty values.
            df = pd.read_excel(self.input_path, skiprows=1)
            # Be tolerant of exports without the banner: if skipping a row hid
            # the real header, fall back to a plain read.
            if not {"Title", "Authors", "Publication Year"}.intersection(df.columns):
                df = pd.read_excel(self.input_path)
            return df
        except Exception as exc:
            raise ExtractionError(f"Failed to read Dimensions XLSX: {exc}") from exc

