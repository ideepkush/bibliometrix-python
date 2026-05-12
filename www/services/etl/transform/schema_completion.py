"""Schema completion for standardized Bibliometrix records."""

from __future__ import annotations

import pandas as pd

from ..constants import FIELD_DEFAULTS, LIST_FIELDS, TARGET_COLUMNS


def _default_for(field: str):
    value = FIELD_DEFAULTS[field]
    if field in LIST_FIELDS:
        return []
    return value


def add_missing_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add missing target columns with the correct empty defaults."""
    output = df.copy()
    for column in TARGET_COLUMNS:
        if column not in output.columns:
            output[column] = [_default_for(column) for _ in range(len(output))]
    return output


def order_target_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return only target columns in the expected order."""
    return df[TARGET_COLUMNS].copy()

