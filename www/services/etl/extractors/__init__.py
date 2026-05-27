"""Source-specific extractors."""

from .cochrane_extractor import CochraneFileExtractor
from .dimensions_extractor import DimensionsExcelExtractor
from .lens_extractor import LensCSVExtractor
from .openalex_api_extractor import OpenAlexAPIExtractor
from .pubmed_api_extractor import PubMedAPIExtractor
from .pubmed_file_extractor import PubMedFileExtractor
from .scopus_extractor import ScopusCSVExtractor

__all__ = [
    "CochraneFileExtractor",
    "DimensionsExcelExtractor",
    "LensCSVExtractor",
    "OpenAlexAPIExtractor",
    "PubMedAPIExtractor",
    "PubMedFileExtractor",
    "ScopusCSVExtractor",
]
