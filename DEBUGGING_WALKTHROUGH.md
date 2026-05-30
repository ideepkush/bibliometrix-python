# Debugging Walkthrough — Making the Analytical Functions Source-Agnostic

The analytical functions in `functions/` and `www/services/` were written
assuming **Web of Science** data: that every column is present, that
multi-value fields are always lists, and that the input DataFrame behaves like
a Shiny reactive value. When fed standardized Scopus / Dimensions / PubMed /
Lens / Cochrane data, several of them crashed.

This document shows the **method** used to fix them. Every patch followed the
same four steps:

> **Symptom → Diagnose (root cause) → Patch (source-agnostic) → Verify.**

A full list of all patches is in `PROJECT_REPORT.md` §8. Four representative
examples are walked through below.

---

## Example 1 — "Main Information" crashes: `'float' object is not iterable`

**Symptom.** Load a dataset, open the **Main Information** panel → the whole
panel shows `Error: 'float' object is not iterable`. Every country-based panel
(Countries Production, Corresponding Authors, Cited Countries) fails the same
way.

**Diagnose.** Read the traceback to the deepest application frame:

```
functions/get_maininformations.py:102  -> metaTagExtraction(df, "AU_CO")
www/services/metatagextraction.py:137  ->  for c1 in C1.iloc[i]:
TypeError: 'float' object is not iterable
```

The function iterates each record's affiliation list `C1.iloc[i]`. For records
with no affiliation, `C1` is a `NaN` **float**, not a list — so the `for` loop
explodes. A WoS-only assumption: *"the affiliation field is always a populated
list."*

**Patch.** Treat any non-list affiliation as empty, and only parse string
entries (`www/services/metatagextraction.py`):

```python
c1_value = C1.iloc[i]
if not isinstance(c1_value, (list, tuple)):
    c1_value = []            # NaN / missing -> no affiliations
for c1 in c1_value:
    if isinstance(c1, str) and pd.notna(c1):
        ...
```

**Verify.** Restart the dashboard → open Main Information → it renders the
dataset summary (Timespan 1985–2020, 281 Sources, 898 Documents, 14.05%
growth). 0 errors. (Before/after screenshots captured.)

---

## Example 2 — Historiograph crashes only *after* opening the Thematic Map

**Symptom.** Each panel works alone, but in the dashboard, opening **Thematic
Map** and then **Historiograph** crashes with:

```
ValueError: 'SR' is both an index level and a column label, which is ambiguous
```

Run on its own, `histNetwork` is fine — so the bug depends on **execution
order**.

**Diagnose.** In the dashboard every module reads the *same* reactive object,
`df.get()`. Instrumenting the shared DataFrame after each panel shows the
mutation point:

```
get_thematic_map(df)  ->  df.index.name changes from None to "SR"
```

The Thematic Map path calls `cocMatrix`, which does `M.index = M["SR"]`. Because
`M` was the caller's DataFrame **by reference** (no copy), this left the shared
frame with an index named `SR` *and* a column named `SR`. The next module
(Historiograph) then hit the ambiguity. This affects **all** databases,
including WoS.

**Patch.** Make `cocMatrix` a pure function — copy at entry so it can't corrupt
its caller (`www/services/cocmatrix.py`):

```python
# was: M = df if isinstance(df, pd.DataFrame) else df.get()
M = (df if isinstance(df, pd.DataFrame) else df.get()).copy()
```

**Verify.** Thematic Map → Historiograph in sequence: no error, the shared
`df.index.name` stays `None`. 65/65 tests pass.

---

## Example 3 — Dimensions standardizes to 100% empty rows

**Symptom.** The schema tests pass for Dimensions, but the standardized output
is *empty* — every column blank, `PY = 0`, `AU = []` for all 500 rows. The
tests only checked the schema/types, so they were green on meaningless data.

**Diagnose.** Compare the raw header the extractor reads against the mapping
keys:

```python
pd.read_excel("Dimensions.xlsx").columns        # -> ['"About the data: ...', 'Unnamed: 1', ...]
pd.read_excel("Dimensions.xlsx", skiprows=1)     # -> ['Rank', 'Publication ID', 'Title', 'Authors', ...]
```

Dimensions exports prepend a one-line copyright banner, so the **real header is
on row 2**. The extractor read row 1 as the header → none of the mapping keys
matched → everything mapped to empty. Then, even after fixing that, `PY` stayed
empty because the mapping used `"Publication Year"` while the actual column is
`"PubYear"`.

**Patch.** Two targeted fixes:

```python
# extractor: skip the banner row (with a fallback if absent)
df = pd.read_excel(self.input_path, skiprows=1)

# mapping: add the real year column name
"PubYear": "PY",
```

**Verify.**

```
Dimensions: 500 rows | PY 100% populated | SR: "Sohda Makoto, 2022, Surgery Today"
```

Lesson: a passing schema test is not the same as correct data — validate that
fields are actually **populated**, not just present.

---

## Example 4 — A short-reference loop that never terminates (`chr()` overflow)

**Symptom.** On Lens data, `metaTagExtraction(df, "SR")` hangs for ~10 minutes
then raises `ValueError: chr() arg not in range(0x110000)`.

**Diagnose.** The duplicate-SR disambiguation loop appends `-a`, `-b`, ... to
repeated short references until none repeat:

```python
while st == 0:
    ind = SR.duplicated()
    if ind.any():
        i += 1
        SR[ind] = SR[ind] + "-" + chr(96 + i)   # i grows forever
```

Nine Lens rows have a missing journal, so their SR is `NaN`. `NaN + "-a"` is
still `NaN`, so those rows can *never* be made unique — the loop spins ~1.1
million times until `chr(96 + i)` exceeds the Unicode range.

**Patch.** Remove the NaN, and replace the fragile loop with a single-pass,
overflow-proof suffixer (`www/services/metatagextraction.py`):

```python
J9 = J9.fillna("NA"); SR = (... ).fillna("NA")        # no NaN can enter
dup_rank = SR.groupby(SR).cumcount()                  # 0,1,2,... per group
SR = SR + dup_rank.map(_dup_suffix)                   # "", "-a", "-b", ... "-aa"
```

**Verify.** Lens: 1000 rows → 1000 unique SRs, 0 NaN, completes instantly.

---

## The pattern

Across all 16 patches the same WoS-only assumptions recurred, and the
source-agnostic fix was always one of:

| WoS assumption | Source-agnostic fix |
|----------------|---------------------|
| A field is always a populated list | Normalize: list stays, string is split, NaN → `[]` |
| The input is a Shiny reactive (`df.get()`) | Accept a plain DataFrame too / defensive `.copy()` |
| The DB is exactly `"Web_of_Science"` | Case-insensitive matching + non-WoS routing |
| A computed matrix is never empty | Guard `None` / empty before using it |
| Author/year/journal are always present | Fall back to `"NA"` / `0` / `""` |

The ETL guarantees the **schema**; these patches make the **functions** stop
assuming the data came from Web of Science.
