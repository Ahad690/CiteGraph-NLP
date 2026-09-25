"""Fetch and verify bibliographic metadata for the thesis reference list.

The writing skill forbids composing BibTeX from memory. Every candidate here
is resolved against Crossref (falling back to OpenAlex); anything that does not
resolve is reported as UNVERIFIED and must not be cited.

    python scripts/verify_references.py --out thesis/evidence
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import httpx

# (citation key, DOI, why it is cited in this thesis)
CANDIDATES: list[tuple[str, str, str]] = [
    # --- citation analysis and bibliometrics ---
    ("garfield1955", "10.1126/science.122.3159.108", "Citation indexing as a tool for science"),
    ("brin1998anatomy", "10.1016/S0169-7552(98)00110-X", "Anatomy of a large-scale hypertextual search engine"),
    ("chen2007cocitation", "10.1002/asi.20317", "CiteSpace / co-citation visual analytics"),
    ("hirsch2005hindex", "10.1073/pnas.0507655102", "h-index"),
    ("waltman2016review", "10.1016/j.joi.2016.02.007", "Review of citation impact indicators"),
    # --- scholarly data infrastructure ---
    ("priem2022openalex", "10.48550/arXiv.2205.01833", "OpenAlex open scholarly catalogue"),
    ("hendricks2020crossref", "10.1162/qss_a_00022", "Crossref as scholarly infrastructure"),
    ("europepmc2015", "10.1093/nar/gku1061", "Europe PMC full-text literature database"),
    ("wang2020mag", "10.1162/qss_a_00021", "Microsoft Academic Graph"),
    ("martin2021oadoi", "10.7717/peerj.4375", "Unpaywall / open access state"),
    # --- citation network structure and dynamics ---
    ("redner1998citation", "10.1007/s100510050359", "Citation distribution statistics"),
    ("newman2001structure", "10.1073/pnas.98.2.404", "Structure of scientific collaboration networks"),
    ("radicchi2008universality", "10.1073/pnas.0806977105", "Universality of citation distributions"),
    ("chen2007gems", "10.1016/j.joi.2006.06.001", "Finding scientific gems with PageRank on a citation network"),
    ("walker2007citerank", "10.1088/1742-5468/2007/06/P06010", "CiteRank: finding scientific gems"),
    # --- biomedical information extraction ---
    ("kim2003genia", "10.1093/bioinformatics/btg1023", "GENIA corpus for biomedical IE"),
    ("lee2020biobert", "10.1093/bioinformatics/btz682", "BioBERT"),
    ("beltagy2019scibert", "10.18653/v1/D19-1371", "SciBERT"),
    ("neumann2019scispacy", "10.18653/v1/W19-5034", "ScispaCy biomedical NLP pipeline"),
    ("marshall2016robotreviewer", "10.1093/jamia/ocv044", "RobotReviewer: automatic risk-of-bias assessment"),
    ("marshall2020trialstreamer", "10.1093/jamia/ocaa163", "Trialstreamer: auto-updated RCT database"),
    ("nye2018ebmnlp", "10.18653/v1/P18-1019", "EBM-NLP corpus: PICO spans in abstracts"),
    ("jin2018pico", "10.18653/v1/W18-2308", "PICO element detection"),
    # --- evidence synthesis and study quality ---
    ("higgins2011cochrane", "10.1136/bmj.d5928", "Cochrane risk of bias tool"),
    ("moher2009prisma", "10.1371/journal.pmed.1000097", "PRISMA reporting guideline"),
    ("ioannidis2005why", "10.1371/journal.pmed.0020124", "Why most published research findings are false"),
    ("button2013power", "10.1038/nrn3475", "Small sample size undermines reliability"),
    # --- document structure / PDF parsing ---
    ("lopez2009grobid", "10.1007/978-3-642-04346-8_62", "GROBID"),
    # --- graph tooling ---
    ("hagberg2008networkx", "10.25080/TCWV9851", "NetworkX"),
    # --- statistical treatment of a small evaluation set (Chapter 3, 6) ---
    ("wilson1927", "10.1080/01621459.1927.10502953", "Wilson score interval"),
    ("brown2001interval", "10.1214/ss/1009213286", "Interval estimation for a binomial proportion"),
    ("agresti1998approximate", "10.1080/00031305.1998.10480550", "Approximate beats exact for binomial intervals"),
    # --- annotation reliability (Chapter 3) ---
    ("cohen1960kappa", "10.1177/001316446002000104", "Cohen's kappa"),
    ("artstein2008kappa", "10.1162/coli.07-034-r2", "Inter-coder agreement for computational linguistics"),
    ("hripcsak2005agreement", "10.1197/jamia.m1733", "Agreement, F-measure and reliability in IR"),
    # --- PageRank parameters (Chapter 4) ---
    ("langville2004deeper", "10.1080/15427951.2004.10129091", "Deeper inside PageRank"),
    ("boldi2005damping", "10.1145/1060745.1060827", "PageRank as a function of the damping factor"),
    # --- age bias in citation-network ranking (Chapter 4, 8) ---
    ("mariani2016milestone", "10.1016/j.joi.2016.10.005", "Time-balanced centrality recovers milestone papers"),
    ("vaccario2017bias", "10.1016/j.joi.2017.05.014", "Age and field bias in citation-network rankings"),
    # --- reading participant-flow diagrams (Section 6.14) ---
    ("schulz2010consort", "10.1136/bmj.c332", "CONSORT 2010 statement and its flow diagram"),
    ("du2020ppocr", "10.48550/arXiv.2009.09941", "PP-OCR, the recogniser RapidOCR exports"),
    # --- classification metrics (Chapter 6) ---
    ("sokolova2009measures", "10.1016/j.ipm.2009.03.002", "Systematic analysis of classification performance measures"),
    ("fawcett2006roc", "10.1016/j.patrec.2005.10.010", "Introduction to ROC analysis"),
    # --- confidence calibration, the thesis's main negative result (Chapter 6, 8) ---
    ("niculescu2005probabilities", "10.1145/1102351.1102430", "Predicting good probabilities with supervised learning"),
    ("guo2017calibration", "10.48550/arXiv.1706.04599", "On calibration of modern neural networks"),
    ("wynants2020prediction", "10.1136/bmj.m1328", "The systematic review the extractor false-positived on"),
    # --- reproducibility (Chapter 3, 7) ---
    ("peng2011reproducible", "10.1126/science.1213847", "Reproducible research in computational science"),
    ("baker2016reproducibility", "10.1038/533452a", "1,500 scientists on reproducibility"),
]


USER_AGENT = "CiteGraph-NLP-thesis/0.1 (mailto:muhammadahadf23@nutech.edu.pk)"

# Crossref throttles a burst. Firing every candidate at once made entries that
# resolve perfectly well come back as FAIL, and because the bibliography is
# generated from this file's output, a throttled run silently dropped good
# references from the thesis. Requests are therefore serialised through a small
# semaphore and a 429 or 5xx is retried rather than believed.
MAX_CONCURRENT = 4
RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
MAX_ATTEMPTS = 4


async def _get(client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response | None:
    """GET with backoff on the statuses that mean 'ask again', not 'no'."""
    delay = 2.0
    for attempt in range(MAX_ATTEMPTS):
        response = await client.get(url, **kwargs)
        if response.status_code not in RETRY_STATUS:
            return response
        if attempt < MAX_ATTEMPTS - 1:
            await asyncio.sleep(delay)
            delay *= 2
    return response


async def resolve(client: httpx.AsyncClient, key: str, doi: str) -> dict:
    record = {"key": key, "doi": doi, "verified": False, "source": None}
    try:
        r = await _get(
            client,
            f"https://api.crossref.org/works/{doi}",
            headers={"User-Agent": USER_AGENT},
        )
        if r.status_code == 200:
            m = r.json().get("message", {})
            record.update({
                "verified": True,
                "source": "crossref",
                "title": (m.get("title") or [None])[0],
                "container": (m.get("container-title") or [None])[0],
                "year": ((m.get("issued") or {}).get("date-parts") or [[None]])[0][0],
                "authors": [
                    " ".join(filter(None, [a.get("given"), a.get("family")]))
                    for a in (m.get("author") or [])
                ][:12],
                "type": m.get("type"),
                "publisher": m.get("publisher"),
                "volume": m.get("volume"),
                "issue": m.get("issue"),
                "page": m.get("page"),
            })
            return record
    except Exception as e:  # noqa: BLE001
        record["crossref_error"] = str(e)

    try:
        r = await _get(client, f"https://api.openalex.org/works/doi:{doi}",
                       headers={"User-Agent": USER_AGENT})
        if r.status_code == 200:
            d = r.json()
            loc = d.get("primary_location") or {}
            record.update({
                "verified": True,
                "source": "openalex",
                "title": d.get("display_name"),
                "container": (loc.get("source") or {}).get("display_name"),
                "year": d.get("publication_year"),
                "authors": [
                    (a.get("author") or {}).get("display_name")
                    for a in (d.get("authorships") or [])
                ][:12],
                "type": d.get("type"),
            })
    except Exception as e:  # noqa: BLE001
        record["openalex_error"] = str(e)
    return record


def to_bibtex(rec: dict) -> str:
    authors = " and ".join(a for a in (rec.get("authors") or []) if a)
    fields = {
        "title": rec.get("title"),
        "author": authors or None,
        "journal": rec.get("container"),
        "year": rec.get("year"),
        "volume": rec.get("volume"),
        "number": rec.get("issue"),
        "pages": rec.get("page"),
        "publisher": rec.get("publisher"),
        "doi": rec.get("doi"),
    }
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields.items() if v)
    return "@article{%s,\n%s\n}" % (rec["key"], body)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="thesis/evidence")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    seen: set[str] = set()
    unique = []
    for key, doi, note in CANDIDATES:
        if doi.lower() in seen:
            print(f"  skip duplicate DOI for {key}")
            continue
        seen.add(doi.lower())
        unique.append((key, doi, note))

    async with httpx.AsyncClient(timeout=40, follow_redirects=True) as client:
        gate = asyncio.Semaphore(MAX_CONCURRENT)

        async def guarded(key: str, doi: str) -> dict:
            async with gate:
                return await resolve(client, key, doi)

        results = await asyncio.gather(*(guarded(k, d) for k, d, _n in unique))

    notes = {k: n for k, _d, n in unique}
    for r in results:
        r["why_cited"] = notes.get(r["key"])

    verified = [r for r in results if r["verified"]]
    unverified = [r for r in results if not r["verified"]]

    for r in sorted(results, key=lambda x: (not x["verified"], x["key"])):
        mark = "ok  " if r["verified"] else "FAIL"
        print(f"  [{mark}] {r['key']:<24} {(r.get('title') or 'UNRESOLVED')[:62]}")

    json_path = os.path.join(args.out, "references_verified.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump({"verified": verified, "unverified": unverified}, fh, indent=2, ensure_ascii=False)

    bib_path = os.path.join(args.out, "references.bib")
    with open(bib_path, "w", encoding="utf-8") as fh:
        fh.write("% Generated by scripts/verify_references.py -- do not hand-edit.\n")
        fh.write("% Every entry resolved against Crossref or OpenAlex.\n\n")
        for r in sorted(verified, key=lambda x: x["key"]):
            fh.write(to_bibtex(r) + "\n\n")

    print(f"\nverified {len(verified)}/{len(results)}")
    if unverified:
        print("UNVERIFIED (must not be cited):")
        for r in unverified:
            print(f"  - {r['key']} ({r['doi']})")
    print(f"written -> {json_path}\n           {bib_path}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
