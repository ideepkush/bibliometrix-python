"""CSV export for standardized Bibliometrix data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..constants import LIST_FIELDS, TARGET_COLUMNS


def serialize_for_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Return a CSV-safe copy of a standardized DataFrame."""
    output = df[TARGET_COLUMNS].copy()
    for field in LIST_FIELDS:
        output[field] = output[field].map(lambda values: "; ".join(values) if isinstance(values, list) else "")
    return output


def export_standardized_csv(df: pd.DataFrame, output_path: str) -> None:
    """Export standardized bibliographic records to a UTF-8 CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    serialize_for_csv(df).to_csv(path, index=False, encoding="utf-8")

