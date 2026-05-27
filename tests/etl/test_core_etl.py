from __future__ import annotations

import sys
import types
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

www_pkg = types.ModuleType("www")
www_pkg.__path__ = [str(ROOT / "www")]
services_pkg = types.ModuleType("www.services")
services_pkg.__path__ = [str(ROOT / "www" / "services")]
sys.modules.setdefault("www", www_pkg)
sys.modules.setdefault("www.services", services_pkg)

from www.services.etl import convert_to_bibliometrix_df
from www.services.etl.constants import LIST_FIELDS, TARGET_COLUMNS
from www.services.etl.export import serialize_for_csv
from www.services.etl.transform.normalizer import normalize_list_field, normalize_year


def test_scopus_csv_standardizes_schema(tmp_path: Path) -> None:
    source_file = tmp_path / "scopus.csv"
    source_file.write_text(
        "Authors,Title,Source title,Year,Cited by,Author Keywords,EID\n"
        "\"Smith J.; Doe A.\",\"Title A\",\"Journal A\",2024,3,\"alpha; beta\",eid-1\n",
        encoding="utf-8",
    )

    df = convert_to_bibliometrix_df("SCOPUS", input_path=str(source_file))

    assert list(df.columns) == TARGET_COLUMNS
    assert df.loc[0, "DB"] == "SCOPUS"
    assert df.loc[0, "TC"] == 3
    assert df.loc[0, "AU"] == ["Smith J.", "Doe A."]
    assert df.loc[0, "DE"] == ["alpha", "beta"]
    assert "Smith" in df.loc[0, "SR"]


def test_dimensions_xlsx_standardizes_schema(tmp_path: Path) -> None:
    source_file = tmp_path / "dimensions.xlsx"
    pd.DataFrame(
        [
            {
                "Authors": "Rossi M.; Lee K.",
                "Title": "Title B",
                "Journal": "Journal B",
                "Publication Year": "2023-01-01",
                "Times cited": "",
                "Dimensions ID": "dim-1",
            }
        ]
    ).to_excel(source_file, index=False)

    df = convert_to_bibliometrix_df("DIMENSIONS", input_path=str(source_file))

    assert list(df.columns) == TARGET_COLUMNS
    assert df.loc[0, "PY"] == 2023
    assert df.loc[0, "TC"] == 0
    assert df.loc[0, "AU"] == ["Rossi M.", "Lee K."]


def test_pubmed_file_standardizes_schema(tmp_path: Path) -> None:
    source_file = tmp_path / "pubmed.txt"
    source_file.write_text(
        "PMID- 123\n"
        "TI  - PubMed title\n"
        "JT  - PubMed Journal\n"
        "DP  - 2024 May\n"
        "AU  - Smith J\n"
        "AU  - Doe A\n"
        "AID - 10.1000/test [doi]\n"
        "AB  - Abstract text\n",
        encoding="utf-8",
    )

    df = convert_to_bibliometrix_df("PUBMED_FILE", input_path=str(source_file))

    assert list(df.columns) == TARGET_COLUMNS
    assert df.loc[0, "PMID"] == "123"
    assert df.loc[0, "DI"] == "10.1000/test"
    assert df.loc[0, "PY"] == 2024
    assert df.loc[0, "AU"] == ["Smith J", "Doe A"]


def test_no_nan_or_none_in_final_output(tmp_path: Path) -> None:
    source_file = tmp_path / "scopus.csv"
    source_file.write_text("Authors,Title\n,\n", encoding="utf-8")

    df = convert_to_bibliometrix_df("SCOPUS", input_path=str(source_file))

    assert not df.isna().any().any()
    for field in LIST_FIELDS:
        assert isinstance(df.loc[0, field], list)


def test_csv_serialization_uses_semicolon(tmp_path: Path) -> None:
    source_file = tmp_path / "scopus.csv"
    source_file.write_text(
        "Authors,Title,Author Keywords\n"
        "\"Smith J.; Doe A.\",\"Title A\",\"alpha; beta\"\n",
        encoding="utf-8",
    )

    df = convert_to_bibliometrix_df("SCOPUS", input_path=str(source_file))
    csv_df = serialize_for_csv(df)

    assert csv_df.loc[0, "AU"] == "Smith J.; Doe A."
    assert csv_df.loc[0, "DE"] == "alpha; beta"


def test_normalizers() -> None:
    assert normalize_year("Published 2024-05-01") == "2024"
    assert normalize_year("unknown") == ""
    assert normalize_list_field("A; B|C\nD") == ["A", "B", "C", "D"]
