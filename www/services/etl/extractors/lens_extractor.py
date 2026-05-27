"""Lens.org CSV export extractor."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..exceptions import ExtractionError
from .base import BaseExtractor


class LensCSVExtractor(BaseExtractor):
    """Read a Lens.org CSV export and return the raw DataFrame.

    Handles the UTF-8 BOM that Lens prepends to every export.
    """

    def __init__(self, input_path: str):
        self.input_path = Path(input_path)

    def extract(self) -> pd.DataFrame:
        if not self.input_path.exists():
            raise ExtractionError(f"Lens file not found: {self.input_path}")
        try:
            # utf-8-sig strips the BOM that Lens always emits
            return pd.read_csv(self.input_path, encoding="utf-8-sig")
        except Exception as exc:
            raise ExtractionError(f"Failed to read {self.input_path}: {exc}") from exc
