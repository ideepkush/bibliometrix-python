# Bibliometrix-Python — Source-Agnostic ETL Pipeline

**Author:** Deepak Kushwaha
**Course:** Data Science — Academic Year 2025/2026
**Professor:** Vincenzo Moscato

---

## 1. Summary

This contribution adds a **source-agnostic ETL pipeline** (`www/services/etl/`)
to Bibliometrix-Python. The pipeline converts bibliographic data from
**7 sources** — Scopus, Dimensions, PubMed (file + API), OpenAlex, Cochrane,
and Lens.org — into the standardized **Web of Science (WoS) schema**
expected by the analytical functions in `functions/` and `www/services/`.

Headline numbers:

| Metric | Value |
|--------|-------|
| Sources supported | **7** (5 file + 2 API) |
| Required columns guaranteed | **24** (full WoS glossary) |
| Files patched for WoS-bug compatibility | **40+** |
| Automated tests | **65 passing** |
| Function compatibility | **96%** on real Scopus/Dimensions/PubMed data |
| Throughput | up to **8,800 records/sec** (Cochrane) |
| CI/CD | GitHub Actions across Python 3.10/3.11/3.12 |
| Honors bonus | API + CSV-loader integrated into Shiny dashboard |

---

## 2. Architecture

```
                ┌────────────────────────────────────┐
                │  convert2df(source, ...)           │  ← single public entry
                └──────────────┬─────────────────────┘
                               │
                ┌──────────────▼─────────────────────┐
                │  Dispatcher (SOURCE_REGISTRY)      │
                │  routes by source name             │
                └──────────────┬─────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────────┐
        │                      │                          │
   ┌────▼────────┐    ┌────────▼─────────┐    ┌──────────▼─────────┐
   │ Extractors  │    │ Mappings (dicts) │    │ Transform pipeline │
   │ (7 sources) │    │ raw col → WoS    │    │ rename→types→SR    │
   └─────────────┘    └──────────────────┘    └──────────┬─────────┘
                                                          │
                                              ┌───────────▼──────────┐
                                              │ Validation (24 cols, │
                                              │  no NaN, list types) │
                                              └───────────┬──────────┘
                                                          │
                                              ┌───────────▼──────────┐
                                              │ Standardized DF      │
                                              │ → CSV / Dashboard /  │
                                              │   Analytical funcs   │
                                              └──────────────────────┘
```

### 2.1 Dispatcher Pattern with Plugin API

`www/services/etl/dispatcher.py` exposes a single registry plus a public
`register_source()` API for third-party extensions:

```python
SOURCE_REGISTRY = {
    "SCOPUS":      {"extractor": ScopusCSVExtractor,      "mapping": SCOPUS_MAPPING,      "mode": "file"},
    "DIMENSIONS":  {"extractor": DimensionsExcelExtractor,"mapping": DIMENSIONS_MAPPING,  "mode": "file"},
    "PUBMED_FILE": {"extractor": PubMedFileExtractor,     "mapping": PUBMED_MAPPING,      "mode": "file"},
    "OPENALEX":    {"extractor": OpenAlexAPIExtractor,    "mapping": OPENALEX_MAPPING,    "mode": "api"},
    "PUBMED_API":  {"extractor": PubMedAPIExtractor,      "mapping": PUBMED_MAPPING,      "mode": "api"},
    "COCHRANE":    {"extractor": CochraneFileExtractor,   "mapping": COCHRANE_MAPPING,    "mode": "file"},
    "LENS":        {"extractor": LensCSVExtractor,        "mapping": LENS_MAPPING,        "mode": "file"},
}

# Plugin API — third-party packages can add new sources without modifying core code
register_source("MY_DB", MyExtractor, MY_MAPPING, mode="file")
```

### 2.2 Mapping Dictionaries (declarative, not procedural)

Each source has a dedicated mapping file under `www/services/etl/mappings/`:
`scopus_mapping.py`, `dimensions_mapping.py`, `pubmed_mapping.py`,
`openalex_mapping.py`, `cochrane_mapping.py`, `lens_mapping.py`.

These are pure Python dicts of `{"source_column": "WoS_field_tag"}` — no
conditional branching, no hardcoded source-specific logic.

### 2.3 Type Contracts

| Field group | Python type | Null default |
|-------------|-------------|--------------|
| `AU, AF, C1, CR, DE, ID` | `list[str]` | `[]` |
| `TC, PY` | `int` | `0` |
| All other (16 fields) | `str` | `""` |

### 2.4 SR Calculated Field

`Author, Year, Journal` format, populated for **every** record.

### 2.5 Validation Module

Programmatically verifies:
1. All 24 mandatory columns exist
2. No `NaN` or `None` values
3. Multi-value columns are real `list[str]`
4. `PY` is a 4-digit year integer (or 0)
5. `DB` is populated for every row

---

## 3. Limitations of Original Python Implementation — Solution Matrix

| # | Original limitation | Where addressed |
|---|---------------------|-----------------|
| 1 | No single entry-point like `convert2df()` | `convert.py::convert_to_bibliometrix_df()` + `convert2df` alias |
| 2 | Scattered transformation logic | `transform/pipeline.py` orchestrator |
| 3 | Weak type enforcement | `transform/type_contracts.py` |
| 4 | Poor NaN/None handling | `transform/normalizer.py` |
| 5 | Implicit WoS dependency | Mapping dicts + case-insensitive DB matching in `histNetwork` |
| 6 | Incomplete column mapping | 24-column TARGET schema enforced |
| 7 | Non-standard reference parsing | Reference parsing in extractors + `normalize_list_field` |

---

## 4. ETL Pipeline Phases (per exam Section 4)

| Phase | Module | Responsibility |
|-------|--------|----------------|
| **1. Extract** | `extractors/` (7 files) | Source-specific raw load (CSV / XLSX / TXT / REST JSON / XML) |
| **2. Transform — Rename** | `transform/renamer.py` | Map raw columns → WoS tags |
| **2. Transform — Type contracts** | `transform/type_contracts.py` | Cast values to required types |
| **2. Transform — Schema completion** | `transform/schema_completion.py` | Add missing columns with defaults |
| **4. Calculated Fields** | `transform/calculated_fields.py` | SR (Short Reference) |
| **5. Validation** | `validation/validator.py` | Schema, type, and null checks |
| **6. Load (Export)** | `export/csv_exporter.py` | CSV serialization with `;` delimiter |

The writing of a single monolithic function is **strictly avoided** —
each phase is a separate module with explicit boundaries.

---

## 5. Advanced Level — API Extraction

### 5.1 OpenAlex
- `https://api.openalex.org/works`
- **Pagination**: `page` + `per-page`
- **Rate limit**: HTTP 429 → exponential backoff (`time.sleep(2**attempt)`)
- **Retries**: 3 attempts per request
- Abstract reconstruction from inverted index
- Author / institution / concept normalization

### 5.2 PubMed API
- NCBI ESearch + EFetch endpoints
- XML payload parsing with `xml.etree.ElementTree`
- Same retry / backoff strategy

### 5.3 Caching Layer (`cache.py`)
Production-grade addition: every API GET is cached on disk for 24 hours
(SHA-1 of url+params key). Speeds up notebooks, CI runs, and dashboard
reloads.

```python
from www.services.etl.cache import cached_get, clear_cache
response = cached_get(url, params={"q": "machine learning"})
removed = clear_cache()  # housekeeping
```

### 5.4 Shared Pipeline
Both API extractors feed through `convert2df()` and inherit **the same
transformation, type contracts, SR calculation, and validation** as file-
based sources — no duplicated logic.

---

## 6. Honors Bonus — Shiny Dashboard Integration

`app.py` now exposes:

### 6.1 API Data Retrieval panel
- Sidebar entry: **Data → API**
- Live OpenAlex / PubMed query with progress feedback
- Standardized preview pushed into the dashboard's reactive `df`

### 6.2 Standardized CSV Loader
- Re-imports any CSV produced by `tests/run_etl.py`
- Re-validates against the WoS schema
- **Pill-badge column coverage** display

Verified live end-to-end in browser:
1. `http://127.0.0.1:8000` → Data → API → "machine learning" / OpenAlex / 20 records
2. "Successfully retrieved 20 records … standardized into the WoS schema"

---

## 7. Performance Benchmarks (real data)

| Source     | Records  | ETL Time | Throughput   |
|------------|----------|----------|--------------|
| SCOPUS     |    1,000 |   0.40s  | 2,503 rec/s  |
| DIMENSIONS |      501 |   0.14s  | 3,673 rec/s  |
| PUBMED_FILE |  10,000 |   1.82s  | 5,481 rec/s  |
| COCHRANE   |    1,126 |   0.13s  | 8,801 rec/s  |
| LENS       |    1,000 |   0.18s  | 5,550 rec/s  |

Sub-second processing for typical research collections.

---

## 8. Function Patches (per exam: "debug and patch hardcoded WoS logic")

### 8.1 `df.get()` reactive-value pattern (39 files)
```python
# Before
data = df.get()
# After
data = df if isinstance(df, pd.DataFrame) else df.get()
```

### 8.2 `df.set(M)` reactive-value pattern (2 service files)
Patched to fall through when given a plain DataFrame.

### 8.3 Missing `typing.List` imports (7 files)
Added `from typing import List, Dict, Optional, Sequence, Union`.

### 8.4 `histNetwork` — case-insensitive DB + non-WoS routing
The function compared `db == "Web_of_Science"` (case-sensitive) and rejected
everything else. Now matches `db.upper().replace("-", "_")` against an
accepted set and routes non-WoS sources through the scopus-compatible code path.

### 8.5 Empty `CR` guard
For sources without cited references (Dimensions, PubMed file), `histNetwork`
returns `None` gracefully. Callers (`get_historiograph`, `get_local_cited_*`)
check for `None` and short-circuit.

### 8.6 NaN-on-empty-data guards (8 functions)
Functions computing `int(max_x)` from possibly-empty Series now guard against
NaN / zero with a safe default.

### 8.7 `get_thematicmap` column count bug
Original code joined `words` into a comma-separated string then re-split,
losing alignment with `sC`. Patched to keep-as-list-throughout.

### 8.8 `get_factorialanalysis` infinity guard
Default `topWordPlot=np.inf` was cast directly via `int()`. Patched to treat
infinity as "all rows".

### 8.9 `biblionetwork` / `cocMatrix` None-result propagation
Added explicit `None` checks before matrix multiplication.

---

## 9. Standard Column Glossary — All 24 Columns Present

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

## 10. Test Results

```
Total tests passing:  65
Test files:           4 (test_core_etl, test_all_sources, test_function_compatibility,
                         test_full_compat_matrix)

Per-source schema compliance:    5/5 sources ✅
Per-source type contracts:      25/25 checks ✅
Function compatibility:         96% across all 3 main sources
```

Continuous Integration (`.github/workflows/etl-tests.yml`) runs every
push and PR across **Python 3.10, 3.11, and 3.12**.

---

## 11. How to Reproduce

```bash
# Run all tests
pytest tests/etl/ -v -s

# CLI sweep over all 5 file sources
python tests/run_etl.py --sweep

# Process a single source
python tests/run_etl.py --source COCHRANE --file sources/Cochrane/citation-export.txt

# Live API query
python tests/run_etl.py --source OPENALEX --query "machine learning" --max 50

# Launch the dashboard with API + CSV loader panels
shiny run app.py
# Open http://127.0.0.1:8000 → Sidebar → Data → API
```

---

## 12. Files Changed

**New ETL package:**
- `www/services/etl/` — dispatcher, extractors (7), mappings (6), transform,
  validation, export, cache
- `tests/conftest.py` — shared fixtures for all 5 file sources
- `tests/etl/test_core_etl.py` — 6 unit tests
- `tests/etl/test_all_sources.py` — 35 schema + type tests
- `tests/etl/test_function_compatibility.py` — 6 integration tests
- `tests/etl/test_full_compat_matrix.py` — broader matrix
- `tests/run_etl.py` — CLI exporter
- `notebooks/ETL_Demonstration.ipynb` — 10-cell walkthrough
- `.github/workflows/etl-tests.yml` — CI/CD
- `PROJECT_REPORT.md` — this report

**Modified (Shiny dashboard):**
- `app.py` — API Data Retrieval + Standardized CSV Loader panels

**Modified (WoS-bug patches):**
- 33 files in `functions/`
- 7 files in `www/services/`
