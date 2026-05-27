"""Cochrane Library → WoS standardized schema mapping."""

COCHRANE_MAPPING = {
    "ID":               "UT",       # Cochrane Record ID becomes the unique tag
    "Title":            "TI",
    "Authors":          "AU",
    "Source":           "SO",
    "Year":             "PY",
    "Volume":           "VL",
    "Issue":            "IS",
    "Pages":            "BP",       # rough mapping — first page if present
    "DOI":              "DI",
    "Publication Type": "DT",
    "Abstract":         "AB",
    "Keywords":         "DE",
    "Language":         "LA",
}
