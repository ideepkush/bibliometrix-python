"""Public entry point for the Bibliometrix-Python ETL pipeline."""

from __future__ import annotations

import pandas as pd

from .dispatcher import resolve_source
from .exceptions import BibliometrixETLError
from .export import export_standardized_csv
from .transform.pipeline import standardize_dataframe
from .validation import validate_standardized_df


def convert_to_bibliometrix_df(
    source: str,
    input_path: str | None = None,
    query: str | None = None,
    output_path: str | None = None,
    max_records: int | None = None,
) -> pd.DataFrame:
    """Convert bibliographic data into the standardized Bibliometrix schema.

    Parameters
    ----------
    source:
        One of SCOPUS, DIMENSIONS, PUBMED_FILE, OPENALEX, or PUBMED_API.
    input_path:
        File path for manually exported file-based sources.
    query:
        Search query for API-based sources.
    output_path:
        Optional path where a standardized CSV should be written.
    max_records:
        Optional record limit for API-based sources.

    Returns
    -------
    pandas.DataFrame
        Standardized Bibliometrix-compatible DataFrame.
    """
    source_name = source.upper().strip()
    config = resolve_source(source_name)
    extractor_class = config["extractor"]
    mapping = config["mapping"]
    mode = config["mode"]

    if mode == "file":
        if not input_path:
            raise BibliometrixETLError(f"input_path is required for {source_name}")
        extractor = extractor_class(input_path)
    else:
        if not query:
            raise BibliometrixETLError(f"query is required for {source_name}")
        extractor = extractor_class(query=query, max_records=max_records)

    raw_df = extractor.extract()
    standardized_df = standardize_dataframe(raw_df, mapping, source=source_name)
    validate_standardized_df(standardized_df)

    if output_path:
        export_standardized_csv(standardized_df, output_path)

    return standardized_df

