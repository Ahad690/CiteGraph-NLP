import asyncio
import ipaddress
import logging
import re
import socket
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

    MAX_REDIRECTS = 5

    @staticmethod
    async def _resolves_to_public_address(url: str) -> bool:
        """True when every address the URL's host resolves to is public.

        The URL here comes straight from the API request body, so without this
        check the server can be pointed at loopback, link-local (cloud metadata)
        or RFC1918 addresses and made to issue requests from inside the trust
        boundary.
        """
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False

        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(
                parsed.hostname, port, type=socket.SOCK_STREAM
            )
        except (socket.gaierror, UnicodeError, ValueError) as exc:
            logger.info("Refusing URL %s: host does not resolve (%s)", url, exc)
            return False

        for info in infos:
            try:
                address = ipaddress.ip_address(info[4][0])
            except ValueError:
                return False
            if (
                address.is_private
                or address.is_loopback
                or address.is_link_local
                or address.is_reserved
                or address.is_multicast
                or address.is_unspecified
            ):
                logger.warning(
                    "Refusing to fetch %s: host resolves to non-public address %s",
                    url, address,
                )
                return False
        return True

    async def resolve_from_page_metadata(self, url: str) -> PaperQuery | None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None

        try:
            # Redirects are followed manually so every hop is re-validated --
            # otherwise a public host could simply redirect to an internal one.
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
                current = url
                for _ in range(self.MAX_REDIRECTS + 1):
                    if not await self._resolves_to_public_address(current):
                        return None

                    response = await client.get(
                        current,
                        headers={"User-Agent": "CiteGraph-NLP/0.1.0"},
                    )
                    if response.is_redirect and response.next_request is not None:
                        current = str(response.next_request.url)
                        continue

                    response.raise_for_status()
                    break
                else:
                    logger.info("Too many redirects while resolving %s", url)
                    return None
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
        doi = IdCanonicalizer.canonicalize(match.group(0).rstrip("."))
        return IdCanonicalizer.strip_doi_view_suffix(doi)
