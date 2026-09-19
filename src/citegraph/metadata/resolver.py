import asyncio
import logging
from typing import List, Dict
from citegraph.models.paper import Paper, PaperQuery
from citegraph.providers.base import get_shared_client, MetadataProvider, ProviderResult
from citegraph.providers.openalex import OpenAlexProvider
from citegraph.providers.crossref import CrossrefProvider
from citegraph.providers.europe_pmc import EuropePMCProvider
from citegraph.metadata.merger import MetadataMerger
from citegraph.input.url_resolver import URLIdentifierResolver
from citegraph.config import settings

logger = logging.getLogger(__name__)

class MetadataResolver:
    def __init__(self):
        self.providers: List[MetadataProvider] = []
        if settings.enable_openalex:
            self.providers.append(OpenAlexProvider())
        if settings.enable_crossref:
            self.providers.append(CrossrefProvider())
        if settings.enable_europe_pmc:
            self.providers.append(EuropePMCProvider())
        
        self.merger = MetadataMerger()
        self.url_resolver = URLIdentifierResolver()

    async def resolve_full(self, query: PaperQuery) -> Paper:
        """Resolve metadata from all enabled providers and merge results.

        Any note worth showing the user is appended to `self.warnings`, which
        the orchestrator drains into the run result.
        """
        self.warnings: list[str] = []

        if query.query_type == "url":
            resolved_query = await self.url_resolver.resolve(query.value)
            if resolved_query:
                logger.info("Resolved URL to %s: %s", resolved_query.query_type, resolved_query.value)
                query = resolved_query
            else:
                # Falling through with query_type still "url" sends the raw URL
                # to every provider, none of which can look one up, and the run
                # dies with "No papers found to merge". Saying so here names
                # the actual problem.
                raise ValueError(
                    f"Could not find a paper identifier on that page: {query.value}. "
                    "Some publishers (IEEE Xplore among them) render the DOI with "
                    "JavaScript or block automated readers, so it cannot be read "
                    "from the page. Paste the DOI itself instead."
                )

        tasks = [provider.resolve(query) for provider in self.providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        provider_results: Dict[str, ProviderResult] = {}
        for provider, result in zip(self.providers, results):
            if isinstance(result, Exception):
                logger.error(f"Provider {provider.name} failed with exception: {result}")
                continue
            provider_results[provider.name] = result

        if not provider_results:
            raise ValueError(f"Failed to resolve metadata from any provider for {query.value}")

        if query.query_type == "title":
            self._warn_about_title_match(query.value, provider_results)

        merged_paper = self.merger.merge(provider_results)
        return merged_paper

    def _warn_about_title_match(
        self, wanted: str, provider_results: Dict[str, ProviderResult]
    ) -> None:
        """Say so when a title search was a guess rather than a lookup.

        A title is not an identifier. Two providers can return different papers
        for the same words, and a famous title attracts mirror records that
        outrank the original. Neither is visible in a result that shows only
        the paper that won.
        """
        matched = {
            name: result for name, result in provider_results.items()
            if result.paper and result.match_score is not None
        }
        if not matched:
            return

        dois = {
            result.paper.doi for result in matched.values() if result.paper.doi
        }
        if len(dois) > 1:
            listed = ", ".join(
                f"{name} -> {result.paper.doi}" for name, result in sorted(matched.items())
                if result.paper.doi
            )
            self.warnings.append(
                f'Providers disagreed about which paper "{wanted}" refers to '
                f"({listed}). The merged record favours the first provider by "
                "precedence. Search by DOI to remove the ambiguity."
            )

        weakest = min(result.match_score for result in matched.values())
        if weakest < 0.85:
            self.warnings.append(
                f'The best title match for "{wanted}" scored {weakest:.2f}, so the '
                "seed paper may not be the one you meant. Search by DOI to be certain."
            )


# Statuses a publisher returns to a script that is not a browser. The link
# works for a person, so they are not evidence that a DOI is dead. Measured
# across the thesis bibliography: 23 of 44 working DOIs answer 403 here.
_BOT_WALL_STATUSES = frozenset({401, 403, 405, 429})


async def doi_is_dead(doi: str) -> bool:
    """True only when doi.org resolves the DOI to a page that is not there.

    Registering a DOI and hosting the page it points at are separate acts, and
    a metadata record can outlive the landing page. A run seeded from such a
    DOI looks completely healthy while its only external link is broken, which
    is what a user reported after searching a title that matched a mirror
    record.

    Anything ambiguous returns False. A warning that fires on a working link
    is worse than no warning.
    """
    if not doi:
        return False
    try:
        client = await get_shared_client()
        response = await client.get(
            f"https://doi.org/{doi}",
            follow_redirects=True,
            timeout=15.0,
            headers={"User-Agent": "CiteGraph-NLP link check"},
        )
    except Exception:  # noqa: BLE001 - a network fault is not proof of a dead DOI
        return False
    if response.status_code in _BOT_WALL_STATUSES:
        return False
    return response.status_code == 404
