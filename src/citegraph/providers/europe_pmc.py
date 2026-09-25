import httpx
import logging
import re
from xml.etree import ElementTree
from typing import Any, Callable, Optional
from datetime import datetime
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from citegraph.providers.base import (
    RETRYABLE_STATUS_CODES,
    MetadataProvider,
    ProviderResult,
    get_shared_client,
    is_transient_error,
)
from citegraph.models.paper import Paper, PaperQuery
from citegraph.models.citation import CitationEdge
from citegraph.utils.ids import IdCanonicalizer

logger = logging.getLogger(__name__)

def _escape_query_value(value: str) -> str:
    """Escape a value going inside an already-quoted Europe PMC term."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _strip_markup(text: str) -> str:
    """Europe PMC abstracts may carry JATS/HTML tags; the extractor wants prose."""
    return " ".join(re.sub(r"<[^>]+>", " ", text).split())


def _quote_term(value: str) -> str:
    """Escape a value for interpolation into a Europe PMC field expression.

    The search grammar is Lucene-like, so an unescaped double quote closes the
    term early and the remainder is parsed as operators. Free-text titles reach
    here straight from the request body (and from third-party page metadata via
    the URL resolver), so they must be escaped rather than trusted.
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _full_text_sections(xml: bytes) -> list[tuple[str, str]]:
    """Read study sections from JATS without pulling in references or tables."""
    root = ElementTree.fromstring(xml)
    body = next((node for node in root.iter() if _local_name(node.tag) == "body"), None)
    if body is None:
        return []

    sections: list[tuple[str, str]] = []

    def visit(section: ElementTree.Element, inherited: str | None = None) -> None:
        title = next((" ".join(child.itertext()) for child in section if _local_name(child.tag) == "title"), "")
        heading = " ".join(title.lower().split())
        if re.search(r"\b(introduction|discussion|conclusions?|references?)\b", heading):
            return
        if re.search(r"\b(results?|findings?|outcomes?)\b", heading):
            label = "results"
        elif inherited != "results" and re.search(r"\b(methods?|methodology|materials?|patients?|participants?|subjects?|study design|recruitment|cohort|population)\b", heading):
            label = "methods"
        else:
            label = inherited

        if label:
            for child in section:
                if _local_name(child.tag) == "p":
                    paragraph = " ".join(" ".join(child.itertext()).split())
                    if paragraph:
                        sections.append((label, paragraph))
        for child in section:
            if _local_name(child.tag) == "sec":
                visit(child, label)

    for child in body:
        if _local_name(child.tag) == "sec":
            visit(child)
    return sections


class EuropePMCProvider:
    name = "europe_pmc"

    def __init__(self):
        self.base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest"

    async def resolve(self, query: PaperQuery) -> ProviderResult:
        try:
            cid = IdCanonicalizer.canonicalize(query.value)
            if not cid:
                return ProviderResult(error="Invalid or empty ID")

            # Format query for Europe PMC
            search_query = None
            if query.query_type == "doi":
                search_query = f'DOI:{_quote_term(cid)}'
            elif query.query_type == "pmid":
                search_query = f'EXT_ID:{_quote_term(cid)}'
            elif query.query_type == "pmcid":
                search_query = f'PMCID:{_quote_term(cid)}'
            elif query.query_type == "title":
                search_query = f'TITLE:{_quote_term(cid)}'
            elif query.query_type == "url":
                # Robust URL parsing to extract DOI, PMID, or PMCID
                from urllib.parse import urlparse, parse_qsl
                parsed = urlparse(cid)
                
                # Check path, query, and even fragment
                search_targets = [parsed.path, parsed.query, parsed.fragment]
                # Also check any query parameter values specifically
                for key, val in parse_qsl(parsed.query):
                    search_targets.append(val)
                
                # Regex patterns
                # DOIs always start with 10. and have prefix/suffix separated by a slash.
                doi_pat = re.compile(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+')
                # PMCIDs start with PMC followed by digits
                pmcid_pat = re.compile(r'PMC\d+', re.I)
                # PMIDs are generally digits, but inside a URL they are often segment/parameter values
                pmid_pat = re.compile(r'\b\d{1,9}\b')
                
                # Search targets in order of priority: DOI, PMCID, then PMID
                # First check for DOI in all targets
                for target in search_targets:
                    if target:
                        doi_match = doi_pat.search(target)
                        if doi_match:
                            doi = IdCanonicalizer.strip_doi_view_suffix(
                                IdCanonicalizer.canonicalize(doi_match.group(0))
                            )
                            search_query = f'DOI:{_quote_term(doi)}'
                            break
                            
                # If no DOI, look for PMCID
                if not search_query:
                    for target in search_targets:
                        if target:
                            pmcid_match = pmcid_pat.search(target)
                            if pmcid_match:
                                pmcid = IdCanonicalizer.canonicalize(pmcid_match.group(0))
                                search_query = f'PMCID:{_quote_term(pmcid)}'
                                break
                                
                # If no DOI or PMCID, check specific URL paths or query params for PMID
                if not search_query:
                    # Common pubmed path pattern: /pubmed/123456
                    if "/pubmed/" in parsed.path:
                        pmid_match = re.search(r'/pubmed/(\d+)', parsed.path, re.I)
                        if pmid_match:
                            pmid = IdCanonicalizer.canonicalize(pmid_match.group(1))
                            search_query = f'EXT_ID:{_quote_term(pmid)}'
                    # Or check query params if they look like pmid/id
                    if not search_query:
                        for key, val in parse_qsl(parsed.query):
                            if key.lower() in ("pmid", "id", "ext_id") and pmid_pat.match(val):
                                pmid = IdCanonicalizer.canonicalize(val)
                                search_query = f'EXT_ID:{_quote_term(pmid)}'
                                break
                    # Or generic digits at the end of pubmed domain path
                    if not search_query and "pubmed.ncbi.nlm.nih.gov" in parsed.netloc:
                        pmid_match = re.search(r'/(\d+)/?$', parsed.path)
                        if pmid_match:
                            pmid = IdCanonicalizer.canonicalize(pmid_match.group(1))
                            search_query = f'EXT_ID:{_quote_term(pmid)}'
                            
                if not search_query:
                    return ProviderResult(error=f"Could not extract a valid DOI, PMID, or PMCID from URL: {cid}")
            
            if not search_query:
                return ProviderResult(error=f"Unsupported Europe PMC query type: {query.query_type}")
                
            response = await self._get(
                f"{self.base_url}/search",
                params={"query": search_query, "format": "json", "resultType": "core"}
            )
            response.raise_for_status()
            data = response.json()

            # An explicit null here would otherwise raise, the same way a null
            # primary_location did in the OpenAlex mapper.
            result_list = data.get("resultList")
            results = (result_list or {}).get("result") or []
            if not results:
                return ProviderResult(error=f"No results found in Europe PMC for {search_query}")

            paper_data = results[0]
            paper = self._map_to_paper(paper_data)
            return ProviderResult(paper=paper, raw_data=paper_data)
        except Exception as e:
            logger.error(f"Europe PMC resolution failed: {e}")
            return ProviderResult(error=str(e))

    def _map_to_paper(self, data: dict[str, Any]) -> Paper:
        paper_id = data.get("id", data.get("pmid", data.get("doi")))
        return Paper(
            paper_id=IdCanonicalizer.canonicalize(paper_id),
            doi=IdCanonicalizer.canonicalize(data.get("doi")),
            pmid=IdCanonicalizer.canonicalize(data.get("pmid")),
            pmcid=IdCanonicalizer.canonicalize(data.get("pmcid")),
            title=data.get("title", "Unknown Title"),
            authors=[a.get("fullName") for a in ((data.get("authorList") or {}).get("author") or []) if a.get("fullName")],
            year=int(data.get("pubYear")) if data.get("pubYear") else None,
            journal=((data.get("journalInfo") or {}).get("journal") or {}).get("title"),
            abstract=data.get("abstractText"),
            source_ids={"europe_pmc": paper_id},
            metadata_confidence=0.85,
            provenance={"europe_pmc": {"retrieved_at": datetime.utcnow().isoformat()}}
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(is_transient_error),
        reraise=True,
    )
    async def _get(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """GET with the same retry policy as the OpenAlex and Crossref providers.

        Europe PMC answers 503 intermittently. Measured on one fixed set of 98
        DOIs, four identical abstract lookups returned 64, 65, 62 and 84
        abstracts, and one open-access lookup lost a whole batch of 12 PMCIDs to
        a single 503. Every call here used to go straight to the client with no
        retry, so a transient fault became missing data, and the same graph
        recovered 6, 11 and 9 populations from full text on three runs.

        Only transient statuses raise inside this helper, so they are retried;
        anything else is returned for the caller to handle as before, which
        keeps a 404 meaning "not held" rather than "failed".
        """
        client = await get_shared_client()
        response = await client.get(url, params=params)
        if response.status_code in RETRYABLE_STATUS_CODES:
            response.raise_for_status()
        return response

    # DOIs per search request. Europe PMC accepts an OR-joined query; keeping
    # the batch modest keeps the URL well inside server limits.
    ABSTRACT_BATCH_SIZE = 25

    async def find_open_access_pmcids_by_doi(
        self, dois: list[str], on_failure: Callable[[int], None] | None = None,
    ) -> dict[str, str]:
        """Map DOIs to open-access PMCIDs, one search per batch.

        `on_failure` is called with the batch size for any batch still failing
        after retries, so the caller can report the gap instead of treating
        those papers as having no open-access copy.
        """
        wanted = list(dict.fromkeys(
            doi for raw in dois if (doi := IdCanonicalizer.canonicalize(raw)).startswith("10.")
        ))
        pmcids: dict[str, str] = {}
        for index in range(0, len(wanted), self.ABSTRACT_BATCH_SIZE):
            chunk = wanted[index:index + self.ABSTRACT_BATCH_SIZE]
            query = "(" + " OR ".join(f'DOI:"{_escape_query_value(doi)}"' for doi in chunk) + ") AND OPEN_ACCESS:Y"
            try:
                response = await self._get(
                    f"{self.base_url}/search",
                    params={"query": query, "format": "json", "resultType": "lite", "pageSize": self.ABSTRACT_BATCH_SIZE * 2},
                )
                response.raise_for_status()
                for item in ((response.json().get("resultList") or {}).get("result") or []):
                    doi = IdCanonicalizer.canonicalize(item.get("doi") or "")
                    pmcid = IdCanonicalizer.canonicalize(item.get("pmcid") or "")
                    if doi in chunk and re.fullmatch(r"PMC\d+", pmcid, re.IGNORECASE):
                        pmcids[doi] = pmcid.upper()
            except Exception as error:
                logger.warning("Europe PMC open-access lookup failed for %d DOIs: %s", len(chunk), error)
                if on_failure is not None:
                    on_failure(len(chunk))
        return pmcids

    async def get_full_text_sections(self, pmcid: str) -> list[tuple[str, str]]:
        pmcid = IdCanonicalizer.canonicalize(pmcid or "").upper()
        if not re.fullmatch(r"PMC\d+", pmcid):
            return []
        try:
            response = await self._get(f"{self.base_url}/{pmcid}/fullTextXML")
            if response.status_code == 404:
                return []
            response.raise_for_status()
            if len(response.content) > 5_000_000:
                logger.warning("Europe PMC full text too large for %s", pmcid)
                return []
            return _full_text_sections(response.content)
        except (httpx.HTTPError, ElementTree.ParseError) as error:
            logger.warning("Europe PMC full text unavailable for %s: %s", pmcid, error)
            return []

    async def get_abstracts_by_doi(
        self, dois: list[str], on_failure: Callable[[int], None] | None = None,
    ) -> dict[str, str]:
        """Fetch abstracts for many DOIs at once.

        OpenAlex has no abstract for a sizeable share of works (28% of a typical
        graph), and population evidence can only be extracted from text. Europe
        PMC carries most of those abstracts, and an OR-joined search returns a
        whole batch in one request.
        """
        wanted: list[str] = []
        for raw in dois:
            doi = IdCanonicalizer.canonicalize(raw)
            if doi.startswith("10.") and doi not in wanted:
                wanted.append(doi)

        abstracts: dict[str, str] = {}
        for i in range(0, len(wanted), self.ABSTRACT_BATCH_SIZE):
            chunk = wanted[i:i + self.ABSTRACT_BATCH_SIZE]
            query = " OR ".join(f'DOI:"{_escape_query_value(d)}"' for d in chunk)
            try:
                response = await self._get(
                    f"{self.base_url}/search",
                    params={
                        "query": query,
                        "format": "json",
                        "resultType": "core",
                        "pageSize": self.ABSTRACT_BATCH_SIZE * 2,
                    },
                )
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                logger.warning("Europe PMC abstract batch failed for %d DOIs: %s", len(chunk), e)
                if on_failure is not None:
                    on_failure(len(chunk))
                continue

            for item in ((data.get("resultList") or {}).get("result") or []):
                doi = IdCanonicalizer.canonicalize(item.get("doi") or "")
                text = item.get("abstractText")
                if doi and text:
                    abstracts[doi] = _strip_markup(text)
        return abstracts

    async def get_references(self, paper_id: str) -> list[CitationEdge]:
        return []

    async def get_citations(self, paper_id: str) -> list[CitationEdge]:
        return []
