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
]


async def resolve(client: httpx.AsyncClient, key: str, doi: str) -> dict:
    record = {"key": key, "doi": doi, "verified": False, "source": None}
    try:
        r = await client.get(
            f"https://api.crossref.org/works/{doi}",
            headers={"User-Agent": "CiteGraph-NLP-thesis/0.1 (mailto:muhammadahadf23@nutech.edu.pk)"},
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
        r = await client.get(f"https://api.openalex.org/works/doi:{doi}")
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
        results = await asyncio.gather(*(resolve(client, k, d) for k, d, _n in unique))

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
