"""Find a trial's participant-flow diagram and download its image.

Two official, open sources, the same ones scripts/collect_flow_diagrams.py
used to build the evaluation set:

  Europe PMC fullTextXML   lists each figure with its caption and image file
                           name; the caption says whether it is a flow diagram
  PMC Article Datasets     NCBI's public AWS bucket (pmc-oa-opendata) holding
                           each open-access article's figure images

The Europe PMC website refuses automated image downloads and PMC's old figure
addresses stopped resolving when its site moved, so the bucket is the supported
route rather than a workaround. Only open-access articles are in it.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from citegraph.providers.base import get_shared_client

logger = logging.getLogger(__name__)

EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
PMC_BUCKET = "https://pmc-oa-opendata.s3.amazonaws.com"
MAX_IMAGE_BYTES = 8_000_000

# The caption test that found a flow diagram in 62% of 60 open-access trials.
FLOW_CAPTION = re.compile(
    r"(?i)consort|flow ?(chart|diagram)|participant flow|trial profile|"
    r"enrol?lment|study flow|patient flow|screening,? (and )?randomi")


@dataclass
class FlowFigure:
    pmcid: str
    caption: str
    image: bytes
    source: str


def _caption_text(fig_xml: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", fig_xml).split())


async def find_flow_diagram(pmcid: str) -> Optional[FlowFigure]:
    """The first figure whose caption marks it as a flow diagram, or None.

    None covers every way of not having one: not open access, no such figure,
    or an image the bucket does not hold. Network errors are logged and also
    return None, since the caller treats all of these as "no diagram to read".
    """
    if not re.fullmatch(r"PMC\d+", pmcid or ""):
        return None
    client = await get_shared_client()
    try:
        xml = await client.get(f"{EUROPE_PMC}/{pmcid}/fullTextXML")
        if xml.status_code != 200:
            return None
        figure = next((m.group(0) for m in re.finditer(r"<fig\b.*?</fig>", xml.text, re.S)
                       if FLOW_CAPTION.search(_caption_text(m.group(0)))), None)
        if figure is None:
            return None
        href = re.search(r'<graphic[^>]*xlink:href="([^"]+)"', figure)
        if not href:
            return None
        name = href.group(1)
        if not re.search(r"\.(jpe?g|png|gif|tiff?)$", name, re.I):
            name += ".jpg"

        listing = await client.get(f"{PMC_BUCKET}/", params={
            "list-type": "2", "prefix": f"{pmcid}.", "max-keys": "200"})
        keys = [k for k in re.findall(r"<Key>([^<]+)</Key>", listing.text) if k.endswith("/" + name)]
        if not keys:
            return None
        key = sorted(keys)[-1]  # the highest article version is current

        image = await client.get(f"{PMC_BUCKET}/{key}")
        if image.status_code != 200 or not image.content or len(image.content) > MAX_IMAGE_BYTES:
            return None
        return FlowFigure(pmcid, _caption_text(figure)[:600], image.content, f"{PMC_BUCKET}/{key}")
    except Exception as error:  # noqa: BLE001 - reported as "no diagram", logged for debugging
        logger.warning("Flow diagram lookup failed for %s: %s", pmcid, error)
        return None
