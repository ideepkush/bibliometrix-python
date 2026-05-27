# Bibliometrix-Python — Source-Agnostic ETL Pipeline

**Author:** Deepak Kushwaha
**Course:** Data Science — Academic Year 2025/2026
**Professor:** Vincenzo Moscato

---

## 1. Summary

This contribution adds a **source-agnostic ETL pipeline** (`www/services/etl/`)
to Bibliometrix-Python. The pipeline converts bibliographic data from
**Scopus, Dimensions, PubMed (file + API), and OpenAlex** into the standardized
**Web of Science (WoS) schema** expected by the analytical functions in
`functions/` and `www/services/`.

It also includes:
- **Live API integration** in the Shiny dashboard (honors bonus)
- **Patches to 50+ analytical functions** so they run on non-WoS data
  (removing hardcoded WoS-specific logic)
- A **validation engine** that programmatically guarantees schema compliance
- A **comprehensive test suite** verifying compatibility across all sources

---

## 2. Architecture

### 2.1 Dispatcher Pattern

`www/services/etl/dispatcher.py` exposes a single registry mapping each
source name to its extractor class and mapping dictionary:

```python
SOURCE_REGISTRY = {
    "SCOPUS":      {"extractor": ScopusCSVExtractor,      "mapping": SCOPUS_MAPPING,      "mode": "file"},
    "DIMENSIONS":  {"extractor": DimensionsExcelExtractor,"mapping": DIMENSIONS_MAPPING,  "mode": "file"},
    "PUBMED_FILE": {"extractor": PubMedFileExtractor,     "mapping": PUBMED_MAPPING,      "mode": "file"},
    "OPENALEX":    {"extractor": OpenAlexAPIExtractor,    "mapping": OPENALEX_MAPPING,    "mode": "api"},
    "PUBMED_API":  {"extractor": PubMedAPIExtractor,      "mapping": PUBMED_MAPPING,      "mode": "api"},
}
```

Adding a new source requires only:
1. A new extractor class implementing `BaseExtractor.extract() -> pd.DataFrame`
2. A new mapping dictionary
3. One entry in `SOURCE_REGISTRY`

### 2.2 Mapping Dictionaries

Each source has a dedicated mapping file under `www/services/etl/mappings/`:
- `scopus_mapping.py`
- `dimensions_mapping.py`
- `pubmed_mapping.py`
- `openalex_mapping.py`

These are pure Python dicts of `{"source_column": "WoS_field_tag"}` — no
conditional branching, no hardcoded source-specific logic.

### 2.3 Type Contracts

`www/services/etl/transform/type_contracts.py` enforces:

| Field group       | Python type | Null default |
|-------------------|-------------|--------------|
| `AU, AF, C1, CR, DE, ID` | `list[str]` | `[]`         |
| `TC, PY`          | `int`       | `0`          |
| All other         | `str`       | `""`         |

`PY` is stored as a 4-digit `int` (changed from `str` during this work) so
that arithmetic operations in functions like `get_annual_production`,
`get_average_citations`, and `get_main_informations` work natively.

### 2.4 Calculated Field (SR)

`www/services/etl/transform/calculated_fields.py` populates the **Short
Reference** field using the format `FirstAuthor, Year, Journal`, falling
back to the project's existing R-style SR logic when applicable.

### 2.5 Validation Module

`www/services/etl/validation/validator.py` enforces:

1. All 24 mandatory columns exist
2. No `NaN` or `None` values
3. Multi-value columns are real `list[str]`
4. `PY` is a 4-digit year integer (or 0)
5. `DB` is populated for every row

---

## 3. ETL Pipeline Phases (per exam Section 4)

| Phase | Module | Responsibility |
|-------|--------|----------------|
| **1. Extract** | `extractors/` | Source-specific raw load (CSV / XLSX / TXT / REST JSON / XML) |
| **2. Transform — Rename** | `transform/renamer.py` | Map raw columns → WoS tags |
| **2. Transform — Type contracts** | `transform/type_contracts.py` | Cast values to required types |
| **2. Transform — Schema completion** | `transform/schema_completion.py` | Add missing columns with defaults |
| **4. Calculated Fields** | `transform/calculated_fields.py` | SR (Short Reference) |
| **5. Validation** | `validation/validator.py` | Schema, type, and null checks |
| **6. Load (Export)** | `export/csv_exporter.py` | CSV serialization with `;` delimiter |

The writing of a single monolithic function is **strictly avoided** —
each phase is a separate module with explicit boundaries.

---

## 4. Advanced Level — API Extraction

### 4.1 OpenAlex (`openalex_api_extractor.py`)
- Uses the public Works API: `https://api.openalex.org/works`
- **Pagination**: `page` + `per-page` parameters
- **Rate limit handling**: HTTP 429 → exponential backoff (`time.sleep(2**attempt)`)
- **Retries**: 3 attempts per request
- Abstract reconstruction from inverted index
- Author / institution / concept normalization

### 4.2 PubMed API (`pubmed_api_extractor.py`)
- Uses NCBI ESearch + EFetch endpoints
- XML payload parsing with `xml.etree.ElementTree`
- Same retry / backoff strategy as OpenAlex

### 4.3 Shared Pipeline
Both API extractors feed through `convert_to_bibliometrix_df()` and
inherit **the same transformation, type contracts, SR calculation, and
validation** as file-based sources — no duplicated logic.

---

## 5. Honors Bonus — Shiny Dashboard Integration

`app.py` now exposes a fully working **API Data Retrieval** panel:

- Sidebar entry: **Data → API**
- Form inputs: platform (OpenAlex / PubMed API), query string, max records
- Live progress feedback and standardized preview table
- The fetched DataFrame is fed into the dashboard's reactive `df` value,
  immediately enabling all downstream analytical modules.

Verified live end-to-end:
1. Open `http://127.0.0.1:8000`
2. Sidebar → Data → API → "machine learning" / OpenAlex / 20 records → Fetch
3. Receive "Successfully retrieved 20 records from OPENALEX and standardized
   into the WoS schema" with preview of standardized columns.

---

## 6. Function Patches (per exam: "debug and patch functions that fail
due to hardcoded WoS logic")

### 6.1 `df.get()` reactive-value pattern (39 files)
Many analytical functions were written for the Shiny reactive container
and called `df.get()` to unwrap it. Patched to handle both reactive
values **and** plain DataFrames:

```python
# Before
data = df.get()

# After
data = df if isinstance(df, pd.DataFrame) else df.get()
```

Affected:
- `functions/get_*.py` — 33 files
- `www/services/biblionetwork.py`
- `www/services/cocmatrix.py`
- `www/services/couplingmap.py`
- `www/services/metatagextraction.py`
- `www/services/termextraction.py`
- `www/services/thematicmap.py`

### 6.2 `df.set(M)` reactive-value pattern (2 service files)
`metaTagExtraction` and `term_extraction` called `df.set(M)` to update
the reactive. Patched to fall through when given a plain DataFrame and
return the modified DataFrame instead.

### 6.3 Missing `typing.List` imports (7 files)
Files using `List[str]` type hints without `from typing import List`.
Fixed by adding the import.

### 6.4 Case-insensitive DB matching in `histNetwork`
The function compared `db == "Web_of_Science"` / `"Scopus"` (case-sensitive),
failing on standardized uppercase tags. Patched to match
`db.upper().replace("-", "_")` against a set of accepted values and to
route non-WoS sources through the scopus-compatible code path.

### 6.5 Empty `CR` guard
For sources that don't export cited references (Dimensions, PubMed file),
`histNetwork` now returns `None` gracefully instead of crashing.
Calling functions (`get_historiograph`, `get_local_cited_authors`,
`get_local_cited_documents`) check for `None` and short-circuit.

### 6.6 NaN-on-empty-data guards (multiple files)
Functions computing `int(max_x)` from possibly-empty Series now guard
against `NaN` / zero with a safe default. Affects:
`get_relevant_authors`, `get_relevant_sources`, `get_local_cited_*`,
`get_cited_countries`, `get_cited_documents`.

### 6.7 `get_thematicmap` column count bug
The original code joined `words` into a comma-separated string then
re-split with `, ` — losing alignment with the `sC` companion list and
raising `"columns must have matching element counts"` on `.explode()`.
Replaced with keep-as-list-throughout logic.

### 6.8 `get_factorialanalysis` infinity guard
The default `topWordPlot=np.inf` was being cast directly via `int()`,
raising `OverflowError`. Patched to treat infinity as "all rows".

### 6.9 `biblionetwork` / `cocMatrix` None-result propagation
Added explicit `None` checks before matrix multiplication when input
data is too sparse.

---

## 7. Standard Column Glossary — All 24 Columns Present

| Tag | Type | Tag | Type | Tag | Type | Tag | Type |
|-----|------|-----|------|-----|------|-----|------|
| DB  | str  | LA  | str  | RP  | str  | IS  | str  |
| UT  | str  | TC  | int  | CR  | list | BP  | str  |
| DI  | str  | AU  | list | DE  | list | EP  | str  |
| PMID| str  | AF  | list | ID  | list | SR  | str  |
| TI  | str  | C1  | list | AB  | str  |     |      |
| SO  | str  | DT  | str  | VL  | str  |     |      |
| JI  | str  | PY  | int  |     |      |     |      |

---

## 8. Test Results

```
ETL Core Tests:        6/6 PASSED
Compatibility Tests:   6/6 PASSED
Total:                12/12 PASSED
```

**Function compatibility across all sources:**

| Source     | Records | Pass rate |
|------------|---------|-----------|
| SCOPUS     | 1,000   | 27/28 (96%) |
| DIMENSIONS | 501     | 27/28 (96%) |
| PUBMED     | 10,000  | 27/28 (96%) |

The remaining failure is `get_thematic_evolution`, which legitimately
requires a user-provided list of years from the Shiny UI — by design,
not a bug.

---

## 9. How to Reproduce

```bash
# Run all tests
pytest tests/etl/ -v -s

# Process a file
python -c "from www.services.etl import convert_to_bibliometrix_df; \
           df = convert_to_bibliometrix_df('SCOPUS', input_path='sources/Scopus/Scopus.csv'); \
           print(df.shape, df.columns.tolist())"

# Process a live API query
python -c "from www.services.etl import convert_to_bibliometrix_df; \
           df = convert_to_bibliometrix_df('OPENALEX', query='machine learning', max_records=20); \
           print(df[['DB','TI','PY']].head())"

# Launch the dashboard with API panel
shiny run app.py
# Then open http://127.0.0.1:8000 → Sidebar → Data → API
```

---

## 10. Files Changed

**New (ETL pipeline):**
- `www/services/etl/` — full package (dispatcher, extractors, mappings, transform, validation, export)
- `tests/etl/test_core_etl.py` — 6 unit tests for the pipeline
- `tests/etl/test_function_compatibility.py` — 6 integration tests
- `PROJECT_REPORT.md` — this report

**Modified (Shiny dashboard):**
- `app.py` — added API Data Retrieval panel

**Modified (WoS-bug patches):**
- 33 files in `functions/`
- 7 files in `www/services/`
