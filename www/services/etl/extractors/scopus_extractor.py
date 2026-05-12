"""Scopus CSV extractor."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..exceptions import ExtractionError
from .base import BaseExtractor


class ScopusCSVExtractor(BaseExtractor):
    """Read manually exported Scopus CSV files."""

    def __init__(self, input_path: str):
        self.input_path = Path(input_path)

    def extract(self) -> pd.DataFrame:
        """Return raw Scopus records as a DataFrame."""
        if not self.input_path.exists():
            raise ExtractionError(f"Scopus file not found: {self.input_path}")
        try:
            return pd.read_csv(self.input_path)
        except Exception as exc:
            raise ExtractionError(f"Failed to read Scopus CSV: {exc}") from exc

