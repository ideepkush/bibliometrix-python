"""PubMed API extractor using NCBI Entrez."""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from typing import Any

import pandas as pd
import requests

from ..exceptions import ExtractionError
from .base import BaseExtractor


class PubMedAPIExtractor(BaseExtractor):
    """Retrieve PubMed records with ESearch and EFetch."""

    SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(self, query: str, max_records: int | None = None):
        self.query = query
        self.max_records = max_records or 100

    def extract(self) -> pd.DataFrame:
        """Return PubMed API records as a raw DataFrame."""
        ids = self._search_ids()
        if not ids:
            return pd.DataFrame()
        xml_text = self._fetch_records(ids)
        return pd.DataFrame(self._parse_xml(xml_text))

    def _get(self, url: str, params: dict[str, Any]) -> requests.Response:
        for attempt in range(3):
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                return response
            if response.status_code in {429, 500, 502, 503, 504}:
                time.sleep(2**attempt)
                continue
            raise ExtractionError(f"PubMed returned HTTP {response.status_code}: {response.text[:200]}")
        raise ExtractionError("PubMed request failed after retries")

    def _search_ids(self) -> list[str]:
        params = {
            "db": "pubmed",
            "term": self.query,
            "retmode": "json",
            "retmax": self.max_records,
        }
        response = self._get(self.SEARCH_URL, params)
        data = response.json()
        return data.get("esearchresult", {}).get("idlist", [])

    def _fetch_records(self, ids: list[str]) -> str:
        params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "xml",
        }
        return self._get(self.FETCH_URL, params).text

    def _parse_xml(self, xml_text: str) -> list[dict[str, Any]]:
        root = ET.fromstring(xml_text)
        records = []
        for article in root.findall(".//PubmedArticle"):
            medline = article.find("MedlineCitation")
            article_node = medline.find("Article") if medline is not None else None
            if medline is None or article_node is None:
                continue
            records.append(self._parse_article(article, medline, article_node))
        return records

    def _parse_article(
        self,
        pubmed_article: ET.Element,
        medline: ET.Element,
        article_node: ET.Element,
    ) -> dict[str, Any]:
        pmid = medline.findtext("PMID", default="")
        journal = article_node.find("Journal")
        journal_title = journal.findtext("Title", default="") if journal is not None else ""
        journal_issue = journal.find("JournalIssue") if journal is not None else None
        pub_date = journal_issue.find("PubDate") if journal_issue is not None else None
        year = pub_date.findtext("Year", default="") if pub_date is not None else ""

        authors = []
        affiliations = []
        for author in article_node.findall(".//Author"):
            last = author.findtext("LastName", default="")
            initials = author.findtext("Initials", default="")
            full = " ".join(part for part in [last, initials] if part)
            if full:
                authors.append(full)
            for affiliation in author.findall(".//Affiliation"):
                if affiliation.text:
                    affiliations.append(affiliation.text)

        article_ids = {
            elem.attrib.get("IdType", ""): elem.text or ""
            for elem in pubmed_article.findall(".//ArticleId")
        }
        abstract_parts = [
            elem.text or ""
            for elem in article_node.findall(".//AbstractText")
            if elem.text
        ]

        return {
            "PMID": pmid,
            "Title": article_node.findtext("ArticleTitle", default=""),
            "Journal": journal_title,
            "Year": year,
            "Publication Type": [
                elem.text or ""
                for elem in article_node.findall(".//PublicationType")
                if elem.text
            ],
            "Language": article_node.findtext("Language", default=""),
            "DOI": article_ids.get("doi", ""),
            "Authors": authors,
            "Author Full Names": authors,
            "Affiliations": sorted(set(affiliations)),
            "Keywords": [
                elem.text or ""
                for elem in medline.findall(".//Keyword")
                if elem.text
            ],
            "MeSH Terms": [
                elem.text or ""
                for elem in medline.findall(".//DescriptorName")
                if elem.text
            ],
            "Abstract": " ".join(abstract_parts),
            "Volume": journal_issue.findtext("Volume", default="") if journal_issue is not None else "",
            "Issue": journal_issue.findtext("Issue", default="") if journal_issue is not None else "",
            "Medline Page": article_node.findtext("Pagination/MedlinePgn", default=""),
        }
