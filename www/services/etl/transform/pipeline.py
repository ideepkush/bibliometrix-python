"""Shared transformation pipeline for every source."""

from __future__ import annotations

import pandas as pd

from .calculated_fields import add_short_reference
from .renamer import rename_columns
from .schema_completion import add_missing_columns, order_target_columns
from .type_contracts import enforce_type_contracts


def standardize_dataframe(
    raw_df: pd.DataFrame,
    mapping: dict[str, str],
    source: str,
) -> pd.DataFrame:
    """Convert a raw source DataFrame into the target Bibliometrix schema."""
    df = rename_columns(raw_df, mapping)
    df = add_missing_columns(df)
    df["DB"] = source
    df = enforce_type_contracts(df)
    df = add_short_reference(df)
    df = enforce_type_contracts(df)
    return order_target_columns(df)

