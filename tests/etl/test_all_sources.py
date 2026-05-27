"""Schema-compliance tests for ALL 5 file-based sources.

Uses the shared fixtures from tests/conftest.py for clean, fast tests.
"""

from __future__ import annotations

import pytest

from www.services.etl.constants import (
    INTEGER_FIELDS,
    LIST_FIELDS,
    STRING_FIELDS,
    TARGET_COLUMNS,
)
from www.services.etl.validation import validate_standardized_df


# ─── Per-source schema checks ────────────────────────────────────────────────
class TestAllSourcesProduceValidSchema:
    """Every source must produce a valid 24-column WoS DataFrame."""

    def test_scopus(self, scopus_df):
        assert len(scopus_df) > 0
        assert list(scopus_df.columns) == TARGET_COLUMNS
        validate_standardized_df(scopus_df)

    def test_dimensions(self, dimensions_df):
        assert len(dimensions_df) > 0
        assert list(dimensions_df.columns) == TARGET_COLUMNS
        validate_standardized_df(dimensions_df)

    def test_pubmed(self, pubmed_df):
        assert len(pubmed_df) > 0
        assert list(pubmed_df.columns) == TARGET_COLUMNS
        validate_standardized_df(pubmed_df)

    def test_cochrane(self, cochrane_df):
        assert len(cochrane_df) > 0
        assert list(cochrane_df.columns) == TARGET_COLUMNS
        validate_standardized_df(cochrane_df)

    def test_lens(self, lens_df):
        assert len(lens_df) > 0
        assert list(lens_df.columns) == TARGET_COLUMNS
        validate_standardized_df(lens_df)


# ─── Parametrized type-contract checks ───────────────────────────────────────
class TestTypeContractsAcrossAllSources:
    """Verify the same type rules apply across all 5 sources."""

    def test_no_nan_anywhere(self, any_source):
        source, df = any_source
        assert not df.isna().any().any(), f"{source} contains NaN"

    def test_list_fields_are_lists(self, any_source):
        source, df = any_source
        for field in LIST_FIELDS:
            assert all(isinstance(v, list) for v in df[field].head(10)), (
                f"{source}: {field} should be list[str]"
            )

    def test_string_fields_are_strings(self, any_source):
        source, df = any_source
        for field in STRING_FIELDS:
            assert all(isinstance(v, str) for v in df[field].head(10)), (
                f"{source}: {field} should be str"
            )

    def test_integer_fields_are_ints(self, any_source):
        source, df = any_source
        for field in INTEGER_FIELDS:
            assert df[field].dtype.kind in ("i", "u"), (
                f"{source}: {field} dtype is {df[field].dtype}"
            )

    def test_sr_populated(self, any_source):
        source, df = any_source
        sr_filled = (df["SR"].str.len() > 0).sum()
        assert sr_filled == len(df), f"{source}: SR not populated for all rows"

    def test_db_field_set(self, any_source):
        source, df = any_source
        assert (df["DB"].str.len() > 0).all(), f"{source}: DB field empty"
