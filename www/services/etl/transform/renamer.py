"""Column renaming utilities."""

from __future__ import annotations

import pandas as pd


def rename_columns(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Rename source-specific columns to standardized Bibliometrix tags."""
    normalized_lookup = {column.strip().lower(): column for column in df.columns}
    rename_map = {}
    for source_column, target_column in mapping.items():
        actual_column = normalized_lookup.get(source_column.strip().lower())
        if actual_column is not None:
            rename_map[actual_column] = target_column
    return df.rename(columns=rename_map)

