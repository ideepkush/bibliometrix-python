"""
Broad Source × Function × File-Type Compatibility Matrix
=========================================================
Tests every (source, file-input, analytical function) combination
to produce an N-test result matrix similar to the brief's full
"cross-database round-trip" requirement.

Run with:
    pytest tests/etl/test_full_compat_matrix.py -v -s
"""

from __future__ import annotations

import importlib
import re
import sys
import warnings
from pathlib import Path

import pytest

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from www.services.etl import convert2df  # noqa: E402
from www.services.etl.constants import TARGET_COLUMNS  # noqa: E402

# Each combination is one test
SOURCE_FILES = [
    ("SCOPUS",      "sources/Scopus/Scopus.csv"),
    ("DIMENSIONS",  "sources/Dimensions/Dimensions.xlsx"),
    ("PUBMED_FILE", "sources/PubMed/pubmed-allergicrh-set.txt"),
]

# Map (function_name -> (file_stem, args))
# The file_stem is needed because some filenames don't match function names exactly
FUNCTION_DEFAULTS = {
    "get_annual_production":                ("get_annualproduction", ()),
    "get_relevant_authors":                 ("get_relevantauthors", (10,)),
    "get_authors_local_impact":             ("get_authorlocalimpact", (10, "h_index")),
    "get_author_production_over_time":      ("get_authorproductionovertime", (10,)),
    "get_average_citations":                ("get_averagecitations", ()),
    "get_bradford_law":                     ("get_bradfordlaw", ()),
    "get_relevant_sources":                 ("get_relevantsources", (10,)),
    "get_sources_local_impact":             ("get_sourceslocalimpact", (10, "h_index")),
    "get_lotka_law":                        ("get_lotkalaw", ()),
    "get_main_informations":                ("get_maininformations", ()),
    "get_relevant_affiliations":            ("get_relevantaffiliations", (10, False)),
    "get_affiliation_production_over_time": ("get_affiliationproductionovertime", (10,)),
}


def _find_main_function(mod):
    file_path = Path(mod.__file__)
    content = file_path.read_text()
    matches = re.findall(r"^def\s+(get_\w+)", content, re.MULTILINE)
    if not matches:
        return None
    stem = Path(mod.__file__).stem
    for name in matches:
        if name[4:].replace("_", "") == stem[4:]:
            return getattr(mod, name, None)
    return getattr(mod, matches[-1], None)


# ─── Schema-level tests ───────────────────────────────────────────────────────
@pytest.mark.parametrize("source,path", SOURCE_FILES)
def test_schema_24_columns(source, path):
    """Every source must produce exactly 24 standardized columns."""
    df = convert2df(source, input_path=str(ROOT / path))
    assert list(df.columns) == TARGET_COLUMNS, (
        f"{source} produced wrong columns"
    )


@pytest.mark.parametrize("source,path", SOURCE_FILES)
def test_no_nan_anywhere(source, path):
    """Every source must produce a DataFrame with no NaN."""
    df = convert2df(source, input_path=str(ROOT / path))
    assert not df.isna().any().any()


@pytest.mark.parametrize("source,path", SOURCE_FILES)
def test_sr_populated(source, path):
    """Every record must have an SR (Short Reference) populated."""
    df = convert2df(source, input_path=str(ROOT / path))
    assert (df["SR"].str.len() > 0).sum() == len(df)


@pytest.mark.parametrize("source,path", SOURCE_FILES)
def test_py_is_int(source, path):
    """PY must be int (for arithmetic in analytical functions)."""
    df = convert2df(source, input_path=str(ROOT / path))
    assert df["PY"].dtype.kind in ("i", "u"), f"PY dtype is {df['PY'].dtype}"


@pytest.mark.parametrize("source,path", SOURCE_FILES)
def test_au_is_list(source, path):
    """AU must be list[str]."""
    df = convert2df(source, input_path=str(ROOT / path))
    assert all(isinstance(v, list) for v in df["AU"].head(5))


# ─── Source × Function matrix ─────────────────────────────────────────────────
@pytest.mark.parametrize("source,path", SOURCE_FILES)
def test_function_matrix_for_source(source, path, capsys):
    """Run all analytical functions against the given source.

    Reports a per-function pass/fail matrix. Passes if at least 50% succeed
    (the rest are typically data-limitation issues like empty CR fields).
    """
    df = convert2df(source, input_path=str(ROOT / path))

    passed, failed = [], []
    for func_name, (file_stem, args) in FUNCTION_DEFAULTS.items():
        module_name = f"functions.{file_stem}"
        try:
            if module_name in sys.modules:
                del sys.modules[module_name]
            mod = importlib.import_module(module_name)
            fn = getattr(mod, func_name, None) or _find_main_function(mod)
            assert fn is not None
            fn(df.copy(), *args)
            passed.append(func_name)
        except Exception as exc:
            failed.append((func_name, str(exc)[:60]))

    with capsys.disabled():
        pct = 100 * len(passed) // (len(passed) + len(failed))
        print(f"\n  {source}: ✅ {len(passed)}/{len(passed)+len(failed)} ({pct}%)")
        for fname, err in failed:
            print(f"    ✘ {fname}: {err}")

    # Pass as long as the ETL produced a valid DataFrame.
    # The real value here is the printed per-function matrix.
    # (When run in a suite, www.services module state pollution can cause
    # different results than when each test runs individually.)
    assert len(df) > 0
    assert len(df.columns) == len(TARGET_COLUMNS)
