#!/usr/bin/env python3
"""
ETL Pipeline CLI Runner
========================
Convenience tool for running the source-agnostic ETL pipeline from
the command line, exporting standardized CSVs that can be fed back
into the dashboard.

Examples
--------
    # Run the full sweep over all bundled sample files
    python tests/run_etl.py --sweep

    # Process a single file
    python tests/run_etl.py --source SCOPUS --file sources/Scopus/Scopus.csv

    # Live API query
    python tests/run_etl.py --source OPENALEX --query "machine learning" --max 50

    # Strict validation (raise on schema violations)
    python tests/run_etl.py --source SCOPUS --file sources/Scopus/Scopus.csv --strict
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from any cwd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from www.services.etl import convert2df  # noqa: E402
from www.services.etl.validation import validate_standardized_df  # noqa: E402

# Default sample files for the --sweep mode (all 5 file-based sources)
SWEEP_TARGETS = [
    ("SCOPUS",      ROOT / "sources/Scopus/Scopus.csv"),
    ("DIMENSIONS",  ROOT / "sources/Dimensions/Dimensions.xlsx"),
    ("PUBMED_FILE", ROOT / "sources/PubMed/pubmed-allergicrh-set.txt"),
    ("COCHRANE",    ROOT / "sources/Cochrane/citation-export.txt"),
    ("LENS",        ROOT / "sources/Lens/Lens.csv"),
]


def _output_path(source: str, input_path: Path | None) -> Path:
    """Compose the output CSV path under out/etl/."""
    out_dir = ROOT / "out" / "etl"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem if input_path else "api_query"
    return out_dir / f"{source.lower()}__{stem}.csv"


def _process_one(
    source: str,
    input_path: Path | None = None,
    query: str | None = None,
    max_records: int | None = None,
    strict: bool = False,
    mailto: str | None = None,
) -> tuple[bool, str]:
    """Run a single ETL job, return (success, message)."""
    try:
        if query:
            df = convert2df(source, query=query, max_records=max_records)
            label = f"{source} (query='{query}', max={max_records})"
        else:
            df = convert2df(source, input_path=str(input_path))
            label = f"{source} ({input_path.name})"

        if strict:
            validate_standardized_df(df)

        out_path = _output_path(source, input_path)
        # Export with semicolon delimiter for list fields
        from www.services.etl.export import serialize_for_csv
        serialize_for_csv(df).to_csv(out_path, index=False, encoding="utf-8")

        return True, f"✅ {label}: {len(df)} records → {out_path.relative_to(ROOT)}"
    except Exception as exc:
        return False, f"❌ {source}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Source-agnostic ETL pipeline runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--sweep", action="store_true",
                        help="Run all bundled sample files (SCOPUS, DIMENSIONS, PUBMED_FILE)")
    parser.add_argument("--source", type=str, default=None,
                        help="Source name: SCOPUS | DIMENSIONS | PUBMED_FILE | OPENALEX | PUBMED_API")
    parser.add_argument("--file", type=str, default=None,
                        help="Input file path (for file-based sources)")
    parser.add_argument("--query", type=str, default=None,
                        help="Search query (for API-based sources)")
    parser.add_argument("--max", type=int, default=100,
                        help="Maximum records to fetch (API sources). Default: 100")
    parser.add_argument("--mailto", type=str, default=None,
                        help="Contact email for polite API usage")
    parser.add_argument("--strict", action="store_true",
                        help="Raise on validation errors (default: best-effort)")
    args = parser.parse_args()

    print("=" * 60)
    print("  Bibliometrix ETL Pipeline Runner")
    print("=" * 60)

    if args.sweep:
        print(f"\nSweeping {len(SWEEP_TARGETS)} bundled samples...\n")
        results = []
        for source, path in SWEEP_TARGETS:
            if not path.exists():
                print(f"⚠️  {source}: skipped (file not found: {path})")
                continue
            success, msg = _process_one(source, input_path=path, strict=args.strict)
            print(msg)
            results.append(success)

        n_pass = sum(results)
        n_total = len(results)
        print(f"\n{'='*60}")
        print(f"Summary: {n_pass}/{n_total} succeeded")
        return 0 if n_pass == n_total else 1

    if not args.source:
        parser.error("Either --sweep or --source is required")

    if args.query:
        success, msg = _process_one(
            args.source, query=args.query,
            max_records=args.max, strict=args.strict, mailto=args.mailto,
        )
    elif args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"❌ File not found: {path}")
            return 1
        success, msg = _process_one(args.source, input_path=path, strict=args.strict)
    else:
        parser.error("--source requires either --file or --query")

    print(msg)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
