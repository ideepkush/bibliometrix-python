"""Source-agnostic ETL pipeline for Bibliometrix-Python."""

from .convert import convert_to_bibliometrix_df

# Alias matching the R bibliometrix function name (convert2df())
convert2df = convert_to_bibliometrix_df

__all__ = ["convert_to_bibliometrix_df", "convert2df"]
