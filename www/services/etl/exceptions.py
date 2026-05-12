"""Custom exceptions for the Bibliometrix ETL pipeline."""


class BibliometrixETLError(Exception):
    """Base exception for ETL failures."""


class UnsupportedSourceError(BibliometrixETLError):
    """Raised when a selected source is not supported."""


class ExtractionError(BibliometrixETLError):
    """Raised when source extraction fails."""


class BibliometrixETLValidationError(BibliometrixETLError):
    """Raised when standardized data violates the target schema."""

