"""Collect CONSORT participant-flow diagrams from open-access trials.

This is the dataset for the computer-vision tester: can reading a trial's
flow diagram tell randomised, enrolled and analysed counts apart better than
the pattern matcher reading the abstract?

    python scripts/collect_flow_diagrams.py

Sources, all official and open:

  Europe PMC REST search   open-access randomised trials, 2015-2024, with
                           abstract and licence
  Europe PMC fullTextXML   finds the figure whose caption marks it as a flow
                           diagram, and its image file name
  PMC Article Datasets     NCBI's public AWS bucket (pmc-oa-opendata), which
                           holds each open-access article's figure images
                           under those same file names

The Europe PMC website refuses automated image downloads and PMC's old figure
addresses stopped working when its site moved, so the AWS bucket is the
supported route for this, not a workaround.

Outputs:
  thesis/evidence/flow_diagrams/manifest.json   committed; fixes the dataset
  data/flow_diagrams/*.jpg                      not committed; licences vary

Each paper is assigned to "dev" or "test" by its PMCID number alone, so the
split is fixed before anything is looked at and cannot be tuned afterwards.
The reader is developed on dev and evaluated once on test.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "thesis", "evidence", "flow_diagrams", "manifest.json")
IMAGES = os.path.join(ROOT, "data", "flow_diagrams")

EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
PMC_BUCKET = "https://pmc-oa-opendata.s3.amazonaws.com"
QUERY = ('PUB_TYPE:"Randomized Controlled Trial" AND OPEN_ACCESS:y AND IN_EPMC:y '
         'AND PUB_YEAR:[2015 TO 2024]')
SAMPLE_SIZE = 60
HEADERS = {"User-Agent": "CiteGraph-NLP research (mailto:muhammadahadf23@nutech.edu.pk)"}

# The caption test used to measure coverage (62% of 60 sampled trials).
FLOW_CAPTION = re.compile(
    r"(?i)consort|flow ?(chart|diagram)|participant flow|trial profile|"
    r"enrol?lment|study flow|patient flow|screening,? (and )?randomi")


def split_for(pmcid: str) -> str:
    """One paper in four goes to development, decided by the PMCID alone."""
    return "dev" if int(pmcid[3:]) % 4 == 0 else "test"


def caption_text(fig_xml: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", fig_xml).split())


async def image_key(client: httpx.AsyncClient, pmcid: str, href: str) -> str | None:
    """Find the figure in the bucket; articles sit under a versioned folder."""
    listing = await client.get(f"{PMC_BUCKET}/", params={
        "list-type": "2", "prefix": f"{pmcid}.", "max-keys": "200"})
    keys = re.findall(r"<Key>([^<]+)</Key>", listing.text)
    matches = [k for k in keys if k.endswith("/" + href)]
    # The highest version is the current one.
    return sorted(matches)[-1] if matches else None


async def collect_one(client: httpx.AsyncClient, hit: dict) -> dict | None:
    pmcid = hit.get("pmcid")
    if not pmcid:
        return None
    xml = await client.get(f"{EUROPE_PMC}/{pmcid}/fullTextXML")
    if xml.status_code != 200:
        return None
    figure = next((m.group(0) for m in re.finditer(r"<fig\b.*?</fig>", xml.text, re.S)
                   if FLOW_CAPTION.search(caption_text(m.group(0)))), None)
    if figure is None:
        return None
    href_match = re.search(r'<graphic[^>]*xlink:href="([^"]+)"', figure)
    if not href_match:
        return None
    href = href_match.group(1)
    if not re.search(r"\.(jpe?g|png|gif|tiff?)$", href, re.I):
        href += ".jpg"

    key = await image_key(client, pmcid, href)
    if key is None:
        return {"pmcid": pmcid, "status": "image_not_in_bucket", "href": href}

    image = await client.get(f"{PMC_BUCKET}/{key}")
    if image.status_code != 200 or not image.content:
        return {"pmcid": pmcid, "status": f"image_http_{image.status_code}", "href": href}
    filename = f"{pmcid}_{os.path.basename(key)}"
    with open(os.path.join(IMAGES, filename), "wb") as fh:
        fh.write(image.content)

    return {
        "pmcid": pmcid,
        "doi": hit.get("doi"),
        "title": hit.get("title"),
        "year": hit.get("pubYear"),
        "journal": ((hit.get("journalInfo") or {}).get("journal") or {}).get("title"),
        "licence": hit.get("license"),
        "split": split_for(pmcid),
        "caption": caption_text(figure)[:600],
        "image": filename,
        "image_source": f"{PMC_BUCKET}/{key}",
        "abstract": re.sub(r"<[^>]+>", " ", hit.get("abstractText") or "").strip(),
        "status": "ok",
    }


async def main() -> int:
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    os.makedirs(IMAGES, exist_ok=True)
    async with httpx.AsyncClient(headers=HEADERS, timeout=60.0, follow_redirects=True) as client:
        search = await client.get(f"{EUROPE_PMC}/search", params={
            "query": QUERY, "format": "json", "pageSize": SAMPLE_SIZE, "resultType": "core"})
        hits = search.json()["resultList"]["result"][:SAMPLE_SIZE]
        gate = asyncio.Semaphore(4)

        async def guarded(hit):
            async with gate:
                try:
                    return await collect_one(client, hit)
                except httpx.HTTPError as error:
                    return {"pmcid": hit.get("pmcid"), "status": f"error_{type(error).__name__}"}

        results = [r for r in await asyncio.gather(*(guarded(h) for h in hits)) if r]

    papers = sorted((r for r in results if r["status"] == "ok"), key=lambda r: r["pmcid"])
    problems = [r for r in results if r["status"] != "ok"]
    manifest = {
        "query": QUERY,
        "sampled": len(hits),
        "with_flow_diagram": len(papers) + len(problems),
        "collected": len(papers),
        "split_rule": "dev when PMCID number % 4 == 0, else test",
        "problems": problems,
        "papers": papers,
    }
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    dev = sum(1 for p in papers if p["split"] == "dev")
    print(f"  sampled {len(hits)} open-access RCTs")
    print(f"  flow diagram identified: {manifest['with_flow_diagram']}")
    print(f"  images collected: {len(papers)}  (dev {dev}, test {len(papers) - dev})")
    for problem in problems:
        print(f"    not collected: {problem['pmcid']} {problem['status']}")
    licences = {}
    for p in papers:
        licences[p["licence"]] = licences.get(p["licence"], 0) + 1
    print(f"  licences: {licences}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
