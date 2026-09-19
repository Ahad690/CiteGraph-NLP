import asyncio
import logging
import re
import time

import fitz
import httpx

from citegraph.providers.base import get_shared_client


logger = logging.getLogger(__name__)
_request_lock = asyncio.Lock()
_last_request = 0.0


class ArxivFullTextProvider:
    MAX_BYTES = 12_000_000
    MAX_PAGES = 12

    async def get_dataset_sections(self, arxiv_id: str) -> str | None:
        if not re.fullmatch(r"\d{4}\.\d{4,5}", arxiv_id):
            return None

        global _last_request
        try:
            async with _request_lock:
                await asyncio.sleep(max(0, 3.0 - (time.monotonic() - _last_request)))
                _last_request = time.monotonic()
                client = await get_shared_client()
                async with client.stream("GET", f"https://arxiv.org/pdf/{arxiv_id}", follow_redirects=True) as response:
                    response.raise_for_status()
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        content.extend(chunk)
                        if len(content) > self.MAX_BYTES:
                            logger.warning("arXiv PDF exceeds size limit: %s", arxiv_id)
                            return None
            if not content.startswith(b"%PDF-"):
                return None
            with fitz.open(stream=bytes(content), filetype="pdf") as document:
                pages = [document[index].get_text("text") for index in range(min(len(document), self.MAX_PAGES))]
            body = "\n".join(pages)
            heading = re.search(
                r"(?im)^\s*(?:\d+(?:\.\d+)*\s+)?(?:training(?: data)?|datasets?|data(?:sets?)?|experiments?|evaluation|experimental setup)\b",
                body,
            )
            if not heading:
                return None
            body = body[heading.start():]
            references = re.search(r"(?im)^\s*(?:\d+\s+)?references\s*$", body)
            if references:
                body = body[:references.start()]
            return " ".join(re.sub(r"-\s*\n", "", body[:100_000]).split())
        except (httpx.HTTPError, RuntimeError, ValueError) as error:
            logger.warning("arXiv PDF unavailable for %s: %s", arxiv_id, error)
            return None
