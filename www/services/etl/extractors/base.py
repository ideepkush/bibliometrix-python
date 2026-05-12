"""Base extractor interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseExtractor(ABC):
    """Base class for source-specific extractors."""

    @abstractmethod
    def extract(self) -> pd.DataFrame:
        """Extract raw records as a DataFrame."""

