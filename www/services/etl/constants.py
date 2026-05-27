"""Shared schema constants for the Bibliometrix ETL pipeline."""

TARGET_COLUMNS = [
    "DB",
    "UT",
    "DI",
    "PMID",
    "TI",
    "SO",
    "JI",
    "PY",
    "DT",
    "LA",
    "TC",
    "AU",
    "AF",
    "C1",
    "RP",
    "CR",
    "DE",
    "ID",
    "AB",
    "VL",
    "IS",
    "BP",
    "EP",
    "SR",
]

STRING_FIELDS = [
    "DB",
    "UT",
    "DI",
    "PMID",
    "TI",
    "SO",
    "JI",
    "DT",
    "LA",
    "RP",
    "AB",
    "VL",
    "IS",
    "BP",
    "EP",
    "SR",
]

INTEGER_FIELDS = ["TC", "PY"]

LIST_FIELDS = ["AU", "AF", "C1", "CR", "DE", "ID"]

FIELD_DEFAULTS = {
    **{field: "" for field in STRING_FIELDS},
    **{field: 0 for field in INTEGER_FIELDS},
    **{field: [] for field in LIST_FIELDS},
}

FILE_SOURCES = {"SCOPUS", "DIMENSIONS", "PUBMED_FILE"}
API_SOURCES = {"OPENALEX", "PUBMED_API"}

