import logging
import re
from urllib.parse import parse_qsl, urlparse

import httpx
from bs4 import BeautifulSoup

from citegraph.models.paper import PaperQuery
from citegraph.utils.ids import IdCanonicalizer

logger = logging.getLogger(__name__)


class URLIdentifierResolver:
    """Resolve article URLs to scholarly identifiers before metadata lookup."""

    DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
    PMCID_PATTERN = re.compile(r"PMC\d+", re.I)
    PMID_PATTERN = re.compile(r"\b\d{1,9}\b")

    DOI_META_KEYS = {
        "citation_doi",
        "dc.identifier",
        "dc.identifier.doi",
        "doi",
        "prism.doi",
    }
    TITLE_META_KEYS = {
        "citation_title",
        "dc.title",
        "og:title",
        "twitter:title",
    }

    async def resolve(self, url: str) -> PaperQuery | None:
        direct = self.resolve_from_url_text(url)
        if direct:
            return direct

        return await self.resolve_from_page_metadata(url)

    def resolve_from_url_text(self, url: str) -> PaperQuery | None:
        parsed = urlparse(url)
        search_targets = [parsed.path, parsed.query, parsed.fragment]
        search_targets.extend(value for _, value in parse_qsl(parsed.query))

        for target in search_targets:
            doi = self._extract_doi(target)
            if doi:
                return PaperQuery(query_type="doi", value=doi)

        for target in search_targets:
            if not target:
                continue
            pmcid_match = self.PMCID_PATTERN.search(target)
            if pmcid_match:
                return PaperQuery(
                    query_type="pmcid",
                    value=IdCanonicalizer.canonicalize(pmcid_match.group(0)),
                )

        if "/pubmed/" in parsed.path:
            pmid_match = re.search(r"/pubmed/(\d+)", parsed.path, re.I)
            if pmid_match:
                return PaperQuery(query_type="pmid", value=pmid_match.group(1))

        for key, value in parse_qsl(parsed.query):
            if key.lower() in ("pmid", "id", "ext_id") and self.PMID_PATTERN.fullmatch(value):
                return PaperQuery(query_type="pmid", value=value)

        if "pubmed.ncbi.nlm.nih.gov" in parsed.netloc:
            pmid_match = re.search(r"/(\d+)/?$", parsed.path)
            if pmid_match:
                return PaperQuery(query_type="pmid", value=pmid_match.group(1))

        return None

    async def resolve_from_page_metadata(self, url: str) -> PaperQuery | None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, max_redirects=5) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "CiteGraph-NLP/0.1.0"},
                )
                response.raise_for_status()
        except Exception as exc:
            logger.info("Could not fetch URL metadata for %s: %s", url, exc)
            return None

        soup = BeautifulSoup(response.text[:500_000], "html.parser")

        doi = self._extract_meta_doi(soup)
        if doi:
            return PaperQuery(query_type="doi", value=doi)

        title = self._extract_meta_title(soup)
        if title:
            return PaperQuery(query_type="title", value=title)

        return None

    def _extract_meta_doi(self, soup: BeautifulSoup) -> str | None:
        for content in self._iter_meta_contents(soup, self.DOI_META_KEYS):
            doi = self._extract_doi(content)
            if doi:
                return doi
        return None

    def _extract_meta_title(self, soup: BeautifulSoup) -> str | None:
        for content in self._iter_meta_contents(soup, self.TITLE_META_KEYS):
            title = " ".join(content.split())
            if len(title) >= 5:
                return title
        return None

    def _iter_meta_contents(self, soup: BeautifulSoup, keys: set[str]):
        for meta in soup.find_all("meta"):
            key = meta.get("name") or meta.get("property")
            content = meta.get("content")
            if key and content and key.lower() in keys:
                yield content

    def _extract_doi(self, value: str | None) -> str | None:
        if not value:
            return None
        match = self.DOI_PATTERN.search(value)
        if not match:
            return None
        return IdCanonicalizer.canonicalize(match.group(0).rstrip("."))
