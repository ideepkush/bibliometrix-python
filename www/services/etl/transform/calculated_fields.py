"""Calculated field generation for Bibliometrix-compatible data."""

from __future__ import annotations

import pandas as pd

from .normalizer import normalize_list_field, normalize_string


def _surname_from_author(author: str) -> str:
    """Extract a practical surname from a normalized author string."""
    text = normalize_string(author)
    if not text:
        return ""
    if "," in text:
        return text.split(",", 1)[0].strip()
    return text.split()[0].strip()


def _fallback_short_reference(row: pd.Series) -> str:
    authors = normalize_list_field(row.get("AU", []))
    surname = _surname_from_author(authors[0]) if authors else ""
    year = normalize_string(row.get("PY", ""))
    source = normalize_string(row.get("SO", ""))
    parts = [part for part in [surname, year, source] if part]
    return ", ".join(parts)


def add_short_reference(df: pd.DataFrame) -> pd.DataFrame:
    """Add SR using a compatible fallback when repository logic is unavailable."""
    output = df.copy()
    if "SR" not in output.columns:
        output["SR"] = ""
    output["SR"] = output.apply(
        lambda row: normalize_string(row.get("SR")) or _fallback_short_reference(row),
        axis=1,
    )
    return output

