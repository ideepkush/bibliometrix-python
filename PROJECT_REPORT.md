# Bibliometrix-Python — Source-Agnostic ETL Pipeline

**Course:** Data Science — Academic Year 2025/2026  
**Professor:** Vincenzo Moscato

| Name | Matricola |
|------|-----------|
| Deepak Kushwaha | D03000258 |
| Subhadip Maity | D03000291 |
| Vedant Gajanan Pawar | D03000257 |
| Vishal Kumar | D03000263 |

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
| Function compatibility | **96%** — 135/140 (27/28 functions × 5 sources) |
| Throughput | up to **8,800 records/sec** (Cochrane) |
| CI/CD | GitHub Actions across Python 3.10/3.11/3.12 |
| Dashboard integration | API query panel + Standardized CSV loader |

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

## 4. ETL Pipeline Phases

| Phase | Module | Responsibility |
|-------|--------|----------------|
| **1. Extract** | `extractors/` (7 files) | Source-specific raw load (CSV / XLSX / TXT / REST JSON / XML) |
| **2. Transform — Rename** | `transform/renamer.py` | Map raw columns → WoS tags |
| **2. Transform — Type contracts** | `transform/type_contracts.py` | Cast values to required types |
| **2. Transform — Schema completion** | `transform/schema_completion.py` | Add missing columns with defaults |
| **4. Calculated Fields** | `transform/calculated_fields.py` | SR (Short Reference) |
| **5. Validation** | `validation/validator.py` | Schema, type, and null checks |
| **6. Load (Export)** | `export/csv_exporter.py` | CSV serialization with `;` delimiter |

No monolithic function is used — each phase is implemented as a separate
module with explicit boundaries, mirroring the design of `convert2df()` in
the R version of bibliometrix.

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
Every API GET is cached on disk for 24 hours (SHA-1 of url + params as key).
This reduces repeated network calls during notebook runs, CI executions,
and dashboard reloads.

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

## 6. Shiny Dashboard Integration

`app.py` exposes a new **API Data Retrieval** panel:

- Sidebar entry: **Data → API**
- Platform selector: OpenAlex / PubMed
- Search-query text input + max-records numeric input
- Live "Fetch from API" button
- Real-time progress feedback ("Fetching N records from … for: '…'")
- Standardized preview table after retrieval
- The fetched DataFrame is pushed into the dashboard's reactive `df`,
  immediately enabling all downstream analytical modules.

Verified live end-to-end in browser:
1. `http://127.0.0.1:8000` → Data → API → "machine learning" / OpenAlex / 20 records
2. "✅ Successfully retrieved 20 records from OPENALEX and standardized into the WoS schema"
3. Preview table shows `DB | UT | TI | PY | AU | TC` columns populated.

### 6.1 Standardized CSV Loader

A second dashboard panel — **"Load a Standardized CSV"** — re-imports any
CSV produced by the ETL pipeline or `tests/run_etl.py` and re-validates
it against the WoS schema, rendering a pill-badge column-coverage map.
This supports the cross-database round-trip described in Section 4.

---

## 7. Performance Benchmarks (real data)

| Source     | Records  | ETL Time | Throughput   |
|------------|----------|----------|--------------|
| SCOPUS     |    1,000 |   0.40s  | 2,503 rec/s  |
| DIMENSIONS |      501 |   0.14s  | 3,673 rec/s  |
| PUBMED_FILE |  10,000 |   1.82s  | 5,481 rec/s  |
| COCHRANE   |    1,126 |   0.13s  | 8,801 rec/s  |
| LENS       |    1,000 |   0.18s  | 5,550 rec/s  |

Measured on a 2024 MacBook Pro, Python 3.13, single-threaded.

---

## 8. Function Patches — Removing Hardcoded WoS-Specific Logic

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

### 8.10 `cocMatrix` in-place mutation of the shared DataFrame
`cocMatrix` set `M.index = M["SR"]` on the DataFrame it received *by
reference*. In the dashboard every module reads the same reactive `df.get()`
object, so after the thematic-map module ran, the shared frame was left with
an index named `SR` while `SR` was still a column. Any module executed
afterwards (e.g. `get_historiograph`) then crashed with
`'SR' is both an index level and a column label, which is ambiguous`. Fixed by
taking a defensive `.copy()` at function entry so `cocMatrix` no longer
corrupts its caller's data — this affected **all** databases, including WoS.

### 8.11 `metaTagExtraction` (`SR`) infinite-loop / `chr()` overflow
The short-reference de-duplication loop appended `-{chr(96 + i)}` to duplicate
`SR` values until none remained. When a record produced a `NaN` short
reference (e.g. Lens rows missing both `JI` and `SO`), `NaN + "-a"` stayed
`NaN`, so those rows could never be made unique. The loop spun ~1.1M times
until `chr(96 + i)` exceeded the Unicode range and raised
`chr() arg not in range(0x110000)`. Fixed by filling the missing journal
field and replacing the loop with a single-pass, vectorized, overflow-proof
suffixer (`-a`, `-b`, … `-z`, `-aa`, …).

### 8.12 `histNetwork` (`wos` branch) — non-iterable `CR` guard
The WoS code path iterated each record's cited-reference list with
`for ref in refs`. When `CR` was missing it was a `NaN` float rather than a
list, raising `TypeError: 'float' object is not iterable` (reproducible on the
bundled WoS sample, which has empty-CR rows). Fixed by normalising `CR` to a
list first — real lists pass through, raw delimited strings are split, and
`NaN`/`None`/other types become an empty list — so records without references
are skipped instead of crashing.

### 8.13 `histNetwork` (`wos` branch) — empty local-citation matrix guard
`WLCR = cocMatrix(..., Field="LCR")` returns `None` when the documents share
no local cited references (common for small or sparse datasets). The next line
did `set(WLCR.columns)`, raising `AttributeError: 'NoneType' object has no
attribute 'columns'`. Added a guard that falls back to an empty zero
self-matrix, so the historiograph network is simply empty instead of crashing.

### 8.14 `metaTagExtraction` (`AU_CO`) — non-iterable affiliation guard
Country extraction iterated each record's affiliation list with
`for c1 in C1.iloc[i]`. When a record had no affiliation, `C1` was a `NaN`
float, raising `TypeError: 'float' object is not iterable`. This crashed the
**Main Information** panel and every country-based module (countries
production, corresponding-author countries, cited countries) on the bundled
WoS sample. Fixed by treating any non-list affiliation value as empty and
guarding that each entry is a string before parsing — confirmed live in the
dashboard (Main Information and Countries Production now render).

### 8.15 `metaTagExtraction` (`SR`) — list/string/NaN author normalization
The short-reference builder did `[x.strip() for x in l]` over each `AU` value,
assuming a list. When the data came from a flat file (the sample XLSX, or any
reloaded CSV) `AU` was a `";"`-delimited **string**, so it iterated single
characters and produced garbage short references; when `AU` was missing it was
a `NaN` float and crashed. Normalised `AU` to a list (pass lists through, split
strings on `;`, map missing to `[]`) so short references — the citation key
used by the historiograph — are always built from author names.

### 8.16 `histNetwork` (`scopus` branch) — list/string/NaN `CR` normalization
The Scopus citation path assumed `CR` entries were lists (`CR.str.len()`,
`for item in sublist`). Reloaded flat data supplies `CR` as a `";"`-delimited
string (or `NaN`), which broke the explode. Normalised `CR` to lists first,
mirroring the `wos()` branch (§8.12). With §8.15 this makes the **historiograph
render in ~1 s on Scopus data** (vs minutes on the heavy WoS branch) —
confirmed live in the dashboard.

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

### 10.1 Automated Test Suite

```
Total tests passing:  65
Test files:           4 (test_core_etl, test_all_sources,
                         test_function_compatibility, test_full_compat_matrix)

Per-source schema compliance:    5/5 sources ✅
Per-source type contracts:      25/25 checks ✅
```

### 10.2 Function Compatibility Matrix

The standardized DataFrame was tested against **28 analytical functions**
from `bibliometrix-python/functions/` on **5 different source databases**:

| Source     | Records  | Pass Rate          |
|------------|----------|--------------------|
| SCOPUS     |   1,000  | **27 / 28 (96%)** ✅ |
| DIMENSIONS |     501  | **27 / 28 (96%)** ✅ |
| PUBMED     |  10,000  | **27 / 28 (96%)** ✅ |
| COCHRANE   |   1,126  | **27 / 28 (96%)** ✅ |
| LENS       |   1,000  | **27 / 28 (96%)** ✅ |
| **TOTAL**  | **13,627** | **135 / 140 (96%)** ✅ |

### 10.3 Functions Successfully Executed (27/28 across all sources)

`get_affiliationproductionovertime`, `get_annualproduction`,
`get_authorlocalimpact`, `get_authorproductionovertime`,
`get_averagecitations`, `get_bradfordlaw`, `get_citedcountries`,
`get_citeddocuments`, `get_correspondingauthorcountries`,
`get_countriesproduction`, `get_countriesproductionovertime`,
`get_factorialanalysis`, `get_historiograph`, `get_localcitedauthors`,
`get_localciteddocuments`, `get_localcitedreferences`,
`get_localcitedsources`, `get_lotkalaw`, `get_maininformations`,
`get_referencesspectroscopy`, `get_relevantaffiliations`,
`get_relevantauthors`, `get_relevantsources`, `get_sourceslocalimpact`,
`get_sourcesproduction`, `get_thematicmap`, `get_worldmapcollaboration`.

### 10.4 Single Remaining Limitation

| Function | Reason | Type |
|----------|--------|------|
| `get_thematicevolution` | Requires user-provided year breakpoints from the Shiny reactive context | UI-dependent, not a data-format issue |

This function is interactive by design — it expects the user to pick year
windows in the dashboard. It works correctly when called from the Shiny UI;
it cannot be tested headlessly with arbitrary year arrays because the
breakpoints must match the data's actual year range and a reactive context
must be present.

### 10.5 Continuous Integration

`.github/workflows/etl-tests.yml` runs every push and PR across
**Python 3.10, 3.11, and 3.12**.

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

# Launch the dashboard
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
