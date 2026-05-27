"""Validation for standardized Bibliometrix DataFrames."""

from __future__ import annotations

import re

import pandas as pd

from ..constants import INTEGER_FIELDS, LIST_FIELDS, STRING_FIELDS, TARGET_COLUMNS
from ..exceptions import BibliometrixETLValidationError


def validate_standardized_df(df: pd.DataFrame) -> None:
    """Raise a clear error when the DataFrame violates the target schema."""
    missing = [column for column in TARGET_COLUMNS if column not in df.columns]
    if missing:
        raise BibliometrixETLValidationError(f"Missing required columns: {', '.join(missing)}")

    if list(df.columns[: len(TARGET_COLUMNS)]) != TARGET_COLUMNS:
        raise BibliometrixETLValidationError("Output columns are not in the target schema order")

    if df[TARGET_COLUMNS].isna().any().any():
        raise BibliometrixETLValidationError("DataFrame contains NaN values after standardization")

    for field in STRING_FIELDS:
        invalid = df[field].map(lambda value: value is None or not isinstance(value, str))
        if invalid.any():
            raise BibliometrixETLValidationError(f"Column {field} must contain strings only")

    for field in INTEGER_FIELDS:
        invalid = df[field].map(lambda value: value is None or not isinstance(value, int))
        if invalid.any():
            raise BibliometrixETLValidationError(f"Column {field} must contain integers only")

    for field in LIST_FIELDS:
        invalid = df[field].map(_is_invalid_list)
        if invalid.any():
            raise BibliometrixETLValidationError(f"Column {field} must contain list[str] values")

    invalid_year = df["PY"].map(
        lambda value: not isinstance(value, int) or (value != 0 and not (1800 <= value <= 2100))
    )
    if invalid_year.any():
        raise BibliometrixETLValidationError("Column PY must be 0 or a four-digit year integer (1800-2100)")

    empty_db = df["DB"].map(lambda value: not value.strip())
    if empty_db.any():
        raise BibliometrixETLValidationError("Column DB must be populated for every row")


def _is_invalid_list(value: object) -> bool:
    if not isinstance(value, list):
        return True
    return any(not isinstance(item, str) for item in value)

