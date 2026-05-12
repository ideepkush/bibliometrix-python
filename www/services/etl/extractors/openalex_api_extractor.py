"""OpenAlex API extractor."""

from __future__ import annotations

import time
from typing import Any

import pandas as pd
import requests

from ..exceptions import ExtractionError
from .base import BaseExtractor


class OpenAlexAPIExtractor(BaseExtractor):
    """Retrieve bibliographic records from the OpenAlex Works API."""

    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, query: str, max_records: int | None = None, per_page: int = 100):
        self.query = query
        self.max_records = max_records or 100
        self.per_page = min(per_page, 200)

    def extract(self) -> pd.DataFrame:
        """Return OpenAlex records as a raw DataFrame."""
        records = []
        page = 1
        try:
            while len(records) < self.max_records:
                params = {
                    "search": self.query,
                    "per-page": min(self.per_page, self.max_records - len(records)),
                    "page": page,
                }
                response = self._get(params)
                results = response.get("results", [])
                if not results:
                    break
                records.extend(self._normalize_work(work) for work in results)
                page += 1
        except Exception as exc:
            raise ExtractionError(f"Failed to retrieve OpenAlex data: {exc}") from exc
        return pd.DataFrame(records[: self.max_records])

    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(3):
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
            if response.status_code in {429, 500, 502, 503, 504}:
                time.sleep(2**attempt)
                continue
            raise ExtractionError(f"OpenAlex returned HTTP {response.status_code}: {response.text[:200]}")
        raise ExtractionError("OpenAlex request failed after retries")

    def _normalize_work(self, work: dict[str, Any]) -> dict[str, Any]:
        primary_location = work.get("primary_location") or {}
        source = primary_location.get("source") or {}
        biblio = work.get("biblio") or {}
        authorships = work.get("authorships") or []
        authors = []
        institutions = []

        for authorship in authorships:
            author = authorship.get("author") or {}
            if author.get("display_name"):
                authors.append(self._normalize_author_name(author["display_name"]))
            for institution in authorship.get("institutions") or []:
                if institution.get("display_name"):
                    institutions.append(institution["display_name"])

        concepts = [
            concept.get("display_name")
            for concept in work.get("concepts") or []
            if concept.get("display_name")
        ]
        keywords = [
            keyword.get("display_name")
            for keyword in work.get("keywords") or []
            if keyword.get("display_name")
        ]

        return {
            "id": work.get("id", ""),
            "doi": work.get("doi", ""),
            "pmid": self._extract_pmid(work),
            "title": work.get("title", ""),
            "publication_year": work.get("publication_year", ""),
            "type": work.get("type", ""),
            "language": work.get("language", ""),
            "cited_by_count": work.get("cited_by_count", 0),
            "authors": authors,
            "author_full_names": authors,
            "institutions": sorted(set(institutions)),
            "concepts": concepts,
            "keywords": keywords,
            "abstract": self._reconstruct_abstract(work.get("abstract_inverted_index")),
            "source": source.get("display_name", ""),
            "volume": biblio.get("volume", ""),
            "issue": biblio.get("issue", ""),
            "first_page": biblio.get("first_page", ""),
            "last_page": biblio.get("last_page", ""),
        }

    def _extract_pmid(self, work: dict[str, Any]) -> str:
        ids = work.get("ids") or {}
        pmid = ids.get("pmid", "")
        return str(pmid).rsplit("/", 1)[-1] if pmid else ""

    def _normalize_author_name(self, display_name: str) -> str:
        """Format OpenAlex display names as 'Surname, Given Names' when possible."""
        name = str(display_name).strip()
        if "," in name:
            return name
        parts = name.split()
        if len(parts) < 2:
            return name
        return f"{parts[-1]}, {' '.join(parts[:-1])}"

    def _reconstruct_abstract(self, inverted_index: dict[str, list[int]] | None) -> str:
        if not inverted_index:
            return ""
        words = []
        for word, positions in inverted_index.items():
            for position in positions:
                words.append((position, word))
        return " ".join(word for _, word in sorted(words))
