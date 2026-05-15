import asyncio
import logging
from typing import List, Dict
from citegraph.models.paper import Paper, PaperQuery
from citegraph.providers.base import MetadataProvider, ProviderResult
from citegraph.providers.openalex import OpenAlexProvider
from citegraph.providers.crossref import CrossrefProvider
from citegraph.metadata.merger import MetadataMerger
from citegraph.config import settings

logger = logging.getLogger(__name__)

class MetadataResolver:
    def __init__(self):
        self.providers: List[MetadataProvider] = []
        if settings.enable_openalex:
            self.providers.append(OpenAlexProvider())
        if settings.enable_crossref:
            self.providers.append(CrossrefProvider())
        
        self.merger = MetadataMerger()

    async def resolve_full(self, query: PaperQuery) -> Paper:
        """Resolve metadata from all enabled providers and merge results."""
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
            
        merged_paper = self.merger.merge(provider_results)
        return merged_paper
