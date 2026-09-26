# API Reference

Every endpoint the backend exposes, with the request shape, the response
shape, and the errors it can return.

The API is a thin layer: it validates input, starts a background job, and
serves the stored result. All the work happens in the pipeline described in
[PROJECT_REPORT.md](../PROJECT_REPORT.md) and, in full detail, in Chapters 4
and 5 of the thesis.

**Base URL (local):** `http://localhost:8000`
**Interactive docs:** `http://localhost:8000/docs` (FastAPI generates these
from the same Pydantic models the endpoints validate against, so they cannot
go out of date)

---

## Authentication

Optional and off by default. Set `API_KEY` and every `/api/*`
endpoint then requires a matching `X-API-Key` header.

```bash
curl -H "X-API-Key: your-key" http://localhost:8000/api/runs/abc123
```

When the variable is unset the server logs a warning at startup and serves
unauthenticated. That is fine for local use and wrong for a public host. The
comparison is done with `hmac.compare_digest`, so a wrong key takes the same
time to reject as a nearly-right one.

| Condition | Response |
|-----------|----------|
| Key set, header correct | request proceeds |
| Key set, header missing or wrong | `401 Unauthorized` |
| Key unset | request proceeds, warning logged at startup |

---

## `GET /health`

Liveness check. Takes no parameters and touches no database, so it stays cheap
enough for an uptime monitor to poll.

```http
GET /health
```

```json
{ "status": "ok" }
```

---

## `GET /version`

Which build is answering. Unauthenticated, beside `/health`, because its purpose
is to let something outside the box ask: the deploy workflow runs
`scripts/check_deployed_build.py` after every release and refuses when the served
`git_sha` is not the commit it deployed. Both fields are absent when the service
is started by hand rather than by the deploy, and the reply says so rather than
inventing a value.

```http
GET /version
```

```json
{
  "service": "citegraph-api",
  "version": "0.1.0",
  "git_sha": "4c982f2a...",
  "built_at": "2026-09-26T18:04:11Z"
}
```

| Field | Type | Notes |
|-------|------|-------|
| `git_sha` | string | The commit this container was built from; `null` when started by hand |
| `built_at` | string | ISO 8601 UTC build time; `null` when started by hand |
| `version` | string | The API version declared in `main.py` |
| `service` | string | Always `citegraph-api` |

---

## `POST /api/runs/{run_id}/technical-evidence`

Re-run dataset-count extraction for one paper of a finished run, on demand. The
counts are read from the abstract, falling back to open-access arXiv full text,
and are what the drawer's "technical evidence" panel shows. Display only: the
answer does not change any weight in the graph.

```http
POST /api/runs/{run_id}/technical-evidence
```

```json
{ "paper_id": "10.12688/f1000research.146897.4" }
```

Returns the extraction for that paper, including a `status` of `not_applicable`
for a paper that is not a computer-science one.

---

## `POST /api/runs/{run_id}/flow-diagram`

Read a trial's participant-flow diagram on demand, for one paper of a finished
run. The figure is fetched from Europe PMC, the numbers in its boxes are read,
and the boxes are returned with their positions so the caller can draw them. Used
by the drawer's flow-diagram panel.

```http
POST /api/runs/{run_id}/flow-diagram
```

```json
{ "paper_id": "PMC11821620" }
```

The reading is display only. It does not affect the foundational ranking, and the
thesis records the held-out measurement of its accuracy separately.

---

## `POST /api/runs`

Start an analysis. Returns immediately with an identifier; the pipeline runs
in the background because a full traversal takes tens of seconds to minutes,
which is well past any reasonable HTTP timeout.

### Request

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `query_type` | string | `auto` | `auto`, `doi`, `pmid`, `pmcid`, `title` or `url` |
| `value` | string | required | the identifier itself |
| `pdf_path` | string | `null` | optional local PDF, must sit under the uploads directory |
| `backward_depth` | int | `2` | how far to follow references, clamped to 0–3 |
| `forward_depth` | int | `1` | how far to follow citing works, clamped to 0–2 |
| `max_total_papers` | int | `100` | hard ceiling on graph size, clamped to 1–200 |
| `use_pdf_parsing` | bool | `true` | read a supplied `pdf_path` as well as the identifier; has no effect when no `pdf_path` is given |

`auto` is the default and works out the type from the shape of the value, so
a caller can post just a value. It is resolved to a concrete type when the
request model is constructed, and the run record stores the concrete type.
Send an explicit type only to override the detection.

Validation per `query_type`:

- `doi` must match `10.xxxx/yyyy`, case-insensitive
- `pmid` is 1 to 9 digits
- `pmcid` is `PMC` followed by digits
- `title` is free text, matched against OpenAlex
- `url` is fetched and mined for an identifier; see the SSRF note below

```bash
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{"query_type":"doi","value":"10.1056/NEJMoa2001017","backward_depth":2}'
```

Depths and paper count are clamped on the server, not only in the UI, so a
crafted request cannot ask for an unbounded traversal.

### Response

```json
{ "run_id": "9f2c1b7e-4a3d-4c8e-b1f0-2d6e5a9c4711", "status": "started" }
```

### Errors

| Status | When |
|--------|------|
| `422` | the body fails validation: a malformed DOI, or a `pdf_path` that resolves outside the uploads directory |
| `500` | the run could not be recorded in the database |
| `401` | API key required and not supplied |

`pdf_path` is checked by a validator on the Pydantic model rather than in the
route, which is why an escaping path comes back as a validation error along
with every other bad field instead of as a separate failure.

---

## `GET /api/runs/{run_id}`

Poll a run. The response shape depends on whether it has finished, so check
`status` before reading the rest.

```http
GET /api/runs/9f2c1b7e-4a3d-4c8e-b1f0-2d6e5a9c4711
```

Before completion you get a `RunStatus`:

```json
{
  "run_id": "9f2c...",
  "status": "running",
  "error": null,
  "created_at": "2026-09-18T11:04:22.118Z"
}
```

On completion the full `RunResult` is returned instead: papers, studies,
population candidates, population resolutions, technical evidence, citation edges, ranked
foundational papers, ranked paths, and any warnings the pipeline accumulated.

`papers[].research_domain` is OpenAlex-field based (`biomedical`,
`computer_science`, `nonclinical`, or `unknown`). Nonclinical papers have
`population_resolutions[].status = "not_applicable"`. The separate
`technical_evidence` array reports explicit CS dataset-example counts found in
abstracts or up to 10 linked arXiv PDFs per run; those counts are not clinical N_eff and do not weight citation
rankings. Older stored runs may have an empty technical-evidence array.

| `status` | Meaning |
|----------|---------|
| `started` | accepted and recorded, pipeline not yet entered |
| `running` | pipeline in progress |
| `completed` | result available |
| `failed` | `error` explains why |

A provider outage degrades the result rather than aborting it: a paper whose
abstract cannot be retrieved still appears as a node, its edges simply carry
no evidential term.

Failure messages are split by cause. A `ValueError` describes the caller's own
query and is echoed back verbatim. Anything else may carry internal detail
such as filesystem paths or driver messages, so the caller gets only a
reference identifier and the detail stays in the server log.

### Errors

| Status | When |
|--------|------|
| `404` | no run with that identifier |

---

## `GET /api/runs/{run_id}/graph`

The citation graph reduced to what a renderer needs, rather than the full
result document. Takes no query parameters.

```json
{
  "nodes": [
    { "id": "W2003241", "label": "Clinical features of ...", "year": 2020, "n_eff": 41 }
  ],
  "links": [
    { "source": "W2003241", "target": "W1982351", "weight": 0.74 }
  ]
}
```

`n_eff` is the resolved study population for that paper, or `null` where none
was extracted. `weight` on a link is the edge's `final_weight`: the
evidence-weighted value, already combined and scaled by extraction confidence.
The structural components that went into it (`base_weight`, `n_score`,
`journal_score`) are not included here; fetch the full result from
`GET /api/runs/{run_id}` if you need to show why an edge is thick.

The key is `links` rather than `edges`, which is the naming most
force-directed graph libraries expect.

---

## Exports

Five formats, all derived from the same stored result. Each sets a
`Content-Disposition` header so a browser downloads rather than displays.

| Endpoint | Format | Use |
|----------|--------|-----|
| `GET /api/runs/{id}/export/json` | JSON | the complete result, pretty-printed |
| `GET /api/runs/{id}/export/csv` | CSV | one row per paper |
| `GET /api/runs/{id}/export/edges.csv` | CSV | one row per citation edge |
| `GET /api/runs/{id}/export/graphml` | GraphML | opens in Gephi, Cytoscape, yEd |
| `GET /api/runs/{id}/export/markdown` | Markdown | a readable summary report |

The CSV exports are written with a UTF-8 byte-order mark so that spreadsheet
software renders accented author names correctly instead of mojibake. This is
a deliberate choice, not an accident of encoding.

```bash
curl -OJ http://localhost:8000/api/runs/9f2c.../export/graphml
```

### Errors

| Status | When |
|--------|------|
| `404` | run does not exist, or has not completed |

---

## Notes on request handling

**URL inputs are validated against SSRF.** When `query_type` is `url`, the
server resolves the hostname and refuses private, loopback, link-local and
reserved address ranges. Redirects are followed manually so that every hop is
re-validated; a public URL that redirects to `169.254.169.254` is rejected at
the second hop rather than the first. Section 5.7 of the thesis covers this.

**Outbound requests share one pooled client.** All three providers use a
single `httpx.AsyncClient` with connection limits and a retry predicate that
distinguishes transient failures (408, 425, 429, 5xx, timeouts) from permanent
ones. A 404 is not retried.

---

## Related documentation

- [Local setup](SETUP.md) — running the API on your machine
- [Deployment](DEPLOYMENT.md) — running it on a server
- [User guide](../USER_GUIDE.md) — using the dashboard rather than the API
- Thesis Appendix A — the same reference with the design rationale attached
