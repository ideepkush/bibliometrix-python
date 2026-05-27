"""Source dispatcher for the Bibliometrix ETL pipeline."""

from __future__ import annotations

from .exceptions import UnsupportedSourceError
from .extractors import (
    CochraneFileExtractor,
    DimensionsExcelExtractor,
    LensCSVExtractor,
    OpenAlexAPIExtractor,
    PubMedAPIExtractor,
    PubMedFileExtractor,
    ScopusCSVExtractor,
)
from .mappings import (
    COCHRANE_MAPPING,
    DIMENSIONS_MAPPING,
    LENS_MAPPING,
    OPENALEX_MAPPING,
    PUBMED_MAPPING,
    SCOPUS_MAPPING,
)

SOURCE_REGISTRY = {
    "SCOPUS": {
        "extractor": ScopusCSVExtractor,
        "mapping": SCOPUS_MAPPING,
        "mode": "file",
    },
    "DIMENSIONS": {
        "extractor": DimensionsExcelExtractor,
        "mapping": DIMENSIONS_MAPPING,
        "mode": "file",
    },
    "PUBMED_FILE": {
        "extractor": PubMedFileExtractor,
        "mapping": PUBMED_MAPPING,
        "mode": "file",
    },
    "OPENALEX": {
        "extractor": OpenAlexAPIExtractor,
        "mapping": OPENALEX_MAPPING,
        "mode": "api",
    },
    "PUBMED_API": {
        "extractor": PubMedAPIExtractor,
        "mapping": PUBMED_MAPPING,
        "mode": "api",
    },
    "COCHRANE": {
        "extractor": CochraneFileExtractor,
        "mapping": COCHRANE_MAPPING,
        "mode": "file",
    },
    "LENS": {
        "extractor": LensCSVExtractor,
        "mapping": LENS_MAPPING,
        "mode": "file",
    },
}


def register_source(name: str, extractor_cls, mapping: dict, mode: str = "file") -> None:
    """Public API: register a custom source extractor at runtime.

    Enables a true plugin architecture — third-party packages can add
    new sources without modifying core code.

    Example
    -------
    >>> from www.services.etl.dispatcher import register_source
    >>> register_source("MY_DB", MyExtractor, MY_MAPPING, mode="file")
    """
    SOURCE_REGISTRY[name.upper().strip()] = {
        "extractor": extractor_cls,
        "mapping": mapping,
        "mode": mode,
    }


def resolve_source(source: str) -> dict[str, object]:
    """Return source configuration for a supported source."""
    normalized = source.upper().strip()
    if normalized not in SOURCE_REGISTRY:
        supported = ", ".join(sorted(SOURCE_REGISTRY))
        raise UnsupportedSourceError(f"Unsupported source '{source}'. Supported sources: {supported}")
    return SOURCE_REGISTRY[normalized]

