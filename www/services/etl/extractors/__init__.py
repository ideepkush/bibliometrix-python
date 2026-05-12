"""Source-specific extractors."""

from .dimensions_extractor import DimensionsExcelExtractor
from .openalex_api_extractor import OpenAlexAPIExtractor
from .pubmed_api_extractor import PubMedAPIExtractor
from .pubmed_file_extractor import PubMedFileExtractor
from .scopus_extractor import ScopusCSVExtractor

__all__ = [
    "DimensionsExcelExtractor",
    "OpenAlexAPIExtractor",
    "PubMedAPIExtractor",
    "PubMedFileExtractor",
    "ScopusCSVExtractor",
]

