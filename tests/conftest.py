"""Shared pytest fixtures for the test suite.

Centralizes path setup, sample-file fixtures, and standardized
DataFrame fixtures so individual test files stay focused and readable.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pytest

# Project root is two levels up from this conftest
ROOT = Path(__file__).resolve().parents[1]

# Make the project importable from any test
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Silence noisy dependency warnings during test runs
warnings.filterwarnings("ignore")


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Absolute path to the project root."""
    return ROOT


# ─── Sample files for each supported source ──────────────────────────────────
@pytest.fixture(scope="session")
def scopus_csv(project_root) -> Path:
    return project_root / "sources/Scopus/Scopus.csv"


@pytest.fixture(scope="session")
def dimensions_xlsx(project_root) -> Path:
    return project_root / "sources/Dimensions/Dimensions.xlsx"


@pytest.fixture(scope="session")
def pubmed_txt(project_root) -> Path:
    return project_root / "sources/PubMed/pubmed-allergicrh-set.txt"


@pytest.fixture(scope="session")
def cochrane_txt(project_root) -> Path:
    return project_root / "sources/Cochrane/citation-export.txt"


@pytest.fixture(scope="session")
def lens_csv(project_root) -> Path:
    return project_root / "sources/Lens/Lens.csv"


# ─── Standardized DataFrames (one per source) ────────────────────────────────
@pytest.fixture(scope="session")
def scopus_df(scopus_csv):
    from www.services.etl import convert2df
    return convert2df("SCOPUS", input_path=str(scopus_csv))


@pytest.fixture(scope="session")
def dimensions_df(dimensions_xlsx):
    from www.services.etl import convert2df
    return convert2df("DIMENSIONS", input_path=str(dimensions_xlsx))


@pytest.fixture(scope="session")
def pubmed_df(pubmed_txt):
    from www.services.etl import convert2df
    return convert2df("PUBMED_FILE", input_path=str(pubmed_txt))


@pytest.fixture(scope="session")
def cochrane_df(cochrane_txt):
    from www.services.etl import convert2df
    return convert2df("COCHRANE", input_path=str(cochrane_txt))


@pytest.fixture(scope="session")
def lens_df(lens_csv):
    from www.services.etl import convert2df
    return convert2df("LENS", input_path=str(lens_csv))


# ─── Parametrization helpers ─────────────────────────────────────────────────
ALL_SOURCES = ["SCOPUS", "DIMENSIONS", "PUBMED_FILE", "COCHRANE", "LENS"]


@pytest.fixture(params=ALL_SOURCES)
def any_source(request, scopus_df, dimensions_df, pubmed_df, cochrane_df, lens_df):
    """Parametrized fixture yielding each source's standardized DataFrame."""
    mapping = {
        "SCOPUS":      scopus_df,
        "DIMENSIONS":  dimensions_df,
        "PUBMED_FILE": pubmed_df,
        "COCHRANE":    cochrane_df,
        "LENS":        lens_df,
    }
    return request.param, mapping[request.param]
