"""Value normalization helpers for bibliographic records."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from typing import Any

import pandas as pd


def is_missing(value: Any) -> bool:
    """Return True when a value should be treated as missing."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    try:
        return bool(pd.isna(value)) and not isinstance(value, (list, tuple, set, dict))
    except (TypeError, ValueError):
        return False


def normalize_string(value: Any) -> str:
    """Normalize a scalar value to a clean string."""
    if is_missing(value):
        return ""
    return str(value).strip()


def normalize_int(value: Any) -> int:
    """Normalize a value to an integer, defaulting invalid values to 0."""
    if is_missing(value):
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return 0
        return int(value)
    text = str(value).strip()
    if not text:
        return 0
    text = text.replace(",", "")
    try:
        return int(float(text))
    except ValueError:
        return 0


def normalize_year(value: Any) -> str:
    """Return a four-digit publication year or an empty string."""
    text = normalize_string(value)
    if not text:
        return ""
    match = re.search(r"\b(18|19|20|21)\d{2}\b", text)
    return match.group(0) if match else ""


def normalize_list_field(value: Any, prefer_comma_split: bool = False) -> list[str]:
    """Normalize source-specific multi-value fields to list[str]."""
    if is_missing(value):
        return []

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        delimiters = [";", "|", "\n", "\r"]
        if prefer_comma_split:
            delimiters.append(",")
        pattern = "|".join(re.escape(delimiter) for delimiter in delimiters)
        parts = re.split(pattern, text)
        return [part.strip() for part in parts if part and part.strip()]

    if isinstance(value, dict):
        return [normalize_string(item) for item in value.values() if normalize_string(item)]

    if isinstance(value, Iterable):
        cleaned = []
        for item in value:
            if is_missing(item):
                continue
            if isinstance(item, str):
                cleaned.extend(normalize_list_field(item, prefer_comma_split=prefer_comma_split))
            else:
                text = normalize_string(item)
                if text:
                    cleaned.append(text)
        return cleaned

    text = normalize_string(value)
    return [text] if text else []

