"""Source dispatcher for the Bibliometrix ETL pipeline."""

from __future__ import annotations

from .exceptions import UnsupportedSourceError
from .extractors import (
    DimensionsExcelExtractor,
    OpenAlexAPIExtractor,
    PubMedAPIExtractor,
    PubMedFileExtractor,
    ScopusCSVExtractor,
)
from .mappings import DIMENSIONS_MAPPING, OPENALEX_MAPPING, PUBMED_MAPPING, SCOPUS_MAPPING

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
}


def resolve_source(source: str) -> dict[str, object]:
    """Return source configuration for a supported source."""
    normalized = source.upper().strip()
    if normalized not in SOURCE_REGISTRY:
        supported = ", ".join(sorted(SOURCE_REGISTRY))
        raise UnsupportedSourceError(f"Unsupported source '{source}'. Supported sources: {supported}")
    return SOURCE_REGISTRY[normalized]

