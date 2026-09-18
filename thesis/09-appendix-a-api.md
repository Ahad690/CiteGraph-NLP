# Appendix A: API Reference

Base URL of the deployed instance: `https://citegraph-api.penora.us`
Interactive documentation: `/docs`

When `API_KEY` is configured, every `/api` route requires an `X-API-Key`
header; `/health` is always open so uptime probes work. In the current
deployment `API_KEY` is unset (see Section 7.5).

## A.1 `GET /health`

```json
{"status": "ok"}
```

## A.2 `POST /api/runs`

Starts an analysis. Returns immediately with an identifier; the analysis runs
in the background because a full run takes tens of seconds to minutes
(Section 6.6).

**Request**

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `query_type` | string | required | `doi`, `pmid`, `pmcid`, `title`, `url` |
| `value` | string | required | The identifier |
| `backward_depth` | int | 2 | References; clamped 0–3 |
| `forward_depth` | int | 1 | Citing works; clamped 0–2 |
| `max_total_papers` | int | 100 | Clamped 1–200 |
| `pdf_path` | string | null | Accepted but not dereferenced; confined to the uploads directory |

**Validation.** `doi` must match `10.xxxx/yyyy`; `pmid` is 1–9 digits; `pmcid`
is `PMC` plus digits; `title` needs at least 5 characters; `url` must have a
scheme and host, and **must not resolve to a private, loopback, link-local or
reserved address** (Section 5.7).

```bash
curl -X POST https://citegraph-api.penora.us/api/runs \
  -H "Content-Type: application/json" \
  -d '{"query_type":"doi","value":"10.1056/NEJMoa2002032",
       "backward_depth":2,"forward_depth":1,"max_total_papers":60}'
```

```json
{"run_id": "a1b2c3d4-...", "status": "started"}
```

## A.3 `GET /api/runs/{run_id}`

While running:

```json
{"run_id": "...", "status": "running", "error": null, "created_at": "..."}
```

When complete, returns the full result: `papers`, `studies`,
`population_candidates`, `population_resolutions`, `citation_edges`,
`ranked_foundational_papers`, `ranked_paths`, `warnings`.

The `warnings` array is worth reading rather than ignoring. It reports how many
abstracts were recovered from a secondary provider and how many duplicate
records were merged, which is what allows a sparse graph to be explained rather
than guessed at (Section 4.7).

On failure, `error` carries a caller-facing message; unexpected internal errors
return a correlation reference rather than the underlying exception text.

## A.4 `GET /api/runs/{run_id}/graph`

Visualisation payload.

```json
{
  "nodes": [{"id": "10.1056/...", "label": "...", "year": 2020, "n_eff": 1099}],
  "links": [{"source": "10.1056/...", "target": "10.1016/...", "weight": 0.43}]
}
```

Every link endpoint is guaranteed present in `nodes` (Section 4.4.2).

## A.5 Exports

All exports return a file with the correct `Content-Type` and a `Content-Disposition` filename, not a JSON envelope (Section 5.8). 
| Endpoint | Type | Contents | |----------|------|----------| | `/export/json` | `application/json` | Full result, indented | | `/export/csv` | `text/csv` | One row per paper: identifiers, authors, journal, `n_eff`, population status and confidence, in/out degree, foundational rank, seed flag | | `/export/edges.csv` | `text/csv` | One row per edge with every weight component | | `/export/markdown` | `text/markdown` | Report: seed details, summary, foundational ranking, population evidence, top citation paths | | `/export/graphml` | `application/xml` | GraphML for Gephi, yEd or Cytoscape Desktop |

Both CSV exports are written with Python's `csv` module, so commas, quotes and
newlines inside titles and journal names are escaped correctly, and carry a
UTF-8 byte-order mark so spreadsheet software renders accented author names.

---
