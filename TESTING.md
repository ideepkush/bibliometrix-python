# Testing Guide — Source-Agnostic ETL Pipeline

This guide maps each test to the exam requirements. Run everything from the
project root:

```bash
cd bibliometrix-python
```

> ⚠️ **Run the dashboard with the project virtualenv** (`./.venv312/bin/python`),
> **not** the system/anaconda Python. The project pins `plotly==5.24.1`
> (`requirements.txt`); with plotly 6.x the Plotly `FigureWidget` charts render
> as empty shells. NLTK corpora (`stopwords`, `wordnet`) are downloaded
> automatically on first import.

---

## 1. Base Level — standardized output runs the analytical functions

**Standardize every raw source to a CSV (the ETL):**

```bash
# All 5 bundled file sources at once
python tests/run_etl.py --sweep            # -> out/etl/*.csv (24 cols, no NaN)

# A single source
python tests/run_etl.py --source DIMENSIONS --file sources/Dimensions/Dimensions.xlsx
```

**Run the automated suite (schema + type contracts + function compatibility):**

```bash
python -m pytest tests/etl/ -v             # 65 tests
```

---

## 2. Advanced Level — API extraction (no manual download)

```bash
python tests/run_etl.py --source OPENALEX   --query "machine learning" --max 50
python tests/run_etl.py --source PUBMED_API --query "machine learning" --max 50
```

Each fetches live (pagination, retries, on-disk cache), standardizes into the
24-column WoS schema, and writes a CSV.

---

## 3. Dashboard Demo — the core proof

```bash
./.venv312/bin/python -m shiny run app.py
# open http://127.0.0.1:8000
```

| Step | Action | Expected |
|------|--------|----------|
| Raw import via ETL | Data → Import raw data → **Scopus** → upload `sources/Scopus/Scopus.csv` → Start | message: *"…uploaded successfully **via the source-agnostic ETL pipeline**"* |
| Other sources | Repeat for Dimensions `.xlsx`, PubMed `.txt`, Lens `.csv`, Cochrane `.txt` | data table populates |
| Run analyses | Main Information · Annual Production · Most Relevant Sources/Authors · Countries · Thematic Map | charts render, no errors |
| API panel | Data → API → OpenAlex → "machine learning" → Fetch | standardized preview table |
| Standardized CSV loader | Data → API → "Load a Standardized CSV" → upload an `out/etl/*.csv` | validation passes, coverage badges green |

**Historiograph:** use a non-WoS source (e.g. Scopus) — it renders in ~1–2 s
through the light `scopus()` branch. The bundled WoS sample's historiograph is
very slow (the `wos()` branch builds an N×N local-citation matrix), so avoid it
for a live demo.

---

## 4. Rubric spot-checks

```bash
# SR comes from the EXISTING repo function (not reimplemented), and Dimensions
# data is actually populated (PY 100%, real short reference):
python -c "import sys,warnings; warnings.filterwarnings('ignore'); sys.path.insert(0,'.'); \
from www.services.etl import convert2df; \
d=convert2df('DIMENSIONS', input_path='sources/Dimensions/Dimensions.xlsx'); \
print('rows', len(d), 'cols', len(d.columns), 'PY%', int((d.PY!=0).mean()*100), '| SR:', d.SR.iloc[0])"
# Expect: rows 500 cols 24 PY% 100 | SR: Sohda Makoto, 2022, Surgery Today
```

---

## Quick smoke test

```bash
python -m pytest tests/etl/ -q && echo "TESTS OK"
python tests/run_etl.py --sweep && echo "ETL OK"
```
