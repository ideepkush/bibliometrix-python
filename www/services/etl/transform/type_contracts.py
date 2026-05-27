"""Type contract enforcement for standardized records."""

from __future__ import annotations

import pandas as pd

from ..constants import INTEGER_FIELDS, LIST_FIELDS, STRING_FIELDS
from .normalizer import normalize_int, normalize_list_field, normalize_string, normalize_year


def _normalize_year_int(value) -> int:
    """Convert a publication year value to int (0 if missing/invalid)."""
    year_str = normalize_year(value)
    return int(year_str) if year_str else 0


def enforce_type_contracts(df: pd.DataFrame) -> pd.DataFrame:
    """Apply scalar, integer, year, and list-field contracts."""
    output = df.copy()

    for field in STRING_FIELDS:
        if field in output.columns:
            output[field] = output[field].map(normalize_string)

    for field in INTEGER_FIELDS:
        if field in output.columns:
            if field == "PY":
                output[field] = output[field].map(_normalize_year_int)
            else:
                output[field] = output[field].map(normalize_int)

    for field in LIST_FIELDS:
        if field in output.columns:
            output[field] = output[field].map(normalize_list_field)

    return output

