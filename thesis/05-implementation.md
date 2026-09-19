# Chapter 5: Implementation

This chapter describes the delivered implementation and, in Sections 5.3 to
5.8, the defects found when the system was systematically instrumented and
measured. The defects are reported in full because they are the most
transferable part of the work: each was invisible to a passing test suite, and
each produced output that looked plausible.

## 5.1 Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Python 3.10+ | Ecosystem for NLP and graph analysis |
| API | FastAPI | Native async, automatic OpenAPI, Pydantic integration |
| Validation | Pydantic v2 | Validation at construction rather than at use |
| HTTP | httpx (async) | Concurrent provider queries, connection pooling |
| Graph | NetworkX [hagberg2008networkx] | Mature PageRank and path algorithms |
| Persistence | SQLite + aiosqlite | Sufficient for run records; no server to operate |
| Retry | Tenacity | Declarative retry policy |
| Frontend | React, TypeScript, Vite, TanStack Router | n/a |
| Visualisation | Cytoscape.js | Interactive graph rendering |
| Testing | pytest, pytest-asyncio, respx | 102 tests; respx mocks HTTP at transport level |

NetworkX was chosen over a graph database because the working set is bounded at
200 nodes. At that scale an in-memory graph is faster than any database round
trip, and Section 6.6 confirms the choice: all graph analytics together account
for 2.5% of runtime. Neo4j appears in the configuration but is not implemented.

## 5.2 Pipeline Orchestration

The orchestrator executes nine stages in sequence: normalise input, resolve
seed, traverse citations, backfill abstracts, extract populations, resolve
populations, weight edges, build graph, run analytics. Each stage is a separate
module; the orchestrator holds no domain logic beyond sequencing and the
assembly of warnings.

Runs execute as background tasks. A `POST` returns a run identifier
immediately, and the client polls. This is necessary because runs take tens of
seconds to minutes, Section 6.6 characterises the distribution, which far
exceeds a reasonable HTTP timeout.

## 5.3 Defect 1: traversal discarding the majority of every graph

### 5.3.1 Symptom

The system produced graphs containing far fewer nodes than expected. For some
inputs it produced a graph containing only the seed paper. This was the
presenting symptom that prompted the measurement campaign.

### 5.3.2 Diagnosis

OpenAlex returns references as OpenAlex work identifiers (`W2741809807`), not
DOIs. The traversal inferred a query type from the identifier's shape:

```python
if target_id.startswith("10."):   query_type = "doi"
elif target_id.isdigit():         query_type = "pmid"
else:                             query_type = "doi"   # W-ids land here
```

A work identifier fell to the final branch and was validated against the DOI
regular expression, which rejected it. The resulting exception was caught by a
broad handler and logged at warning level, so the paper was silently dropped.

Measurement on a representative seed:

```
target identifier kinds : {'W-id': 21, 'doi': 19}
constructible as a query: 19     REJECTED: 21
```

Every OpenAlex-sourced reference was discarded. Only Crossref's DOI-formatted
references survived. Where Crossref holds no reference list, which is common,
since deposit is at publisher discretion, the result was a graph of one node:

```
references for PMID 32109013 : OpenAlex 21, Crossref 0  ->  usable nodes 0
```

### 5.3.3 A second, independent defect in the same component

Forward citations were always empty. The OpenAlex `cites` filter accepts work
identifiers only, but the code passed a DOI-prefixed form:

```
filter=cites:doi:10.1056/nejmoa2002032   ->  HTTP 200, meta.count = 0
filter=cites:W3008827533                 ->  HTTP 200, meta.count = 30606
```

This is the more instructive of the two faults. The malformed query returned
**HTTP 200 with a count of zero** rather than an error. No exception was
raised, no log line was emitted, and the system reported "this paper has no
citing works", a statement that is occasionally true and therefore
unremarkable.

### 5.3.4 Resolution

The traversal was rewritten as the level-synchronous BFS described in
Section 4.4, with an alias table collapsing all identifier forms onto one
canonical `paper_id`, and metadata fetched in batches of fifty through the
OpenAlex `openalex_id` and `doi` filters. Forward citation queries resolve the
seed to a work identifier before filtering.

| Measure | Before | After |
|---------|-------:|------:|
| Forward citations (seed) | 0 | 34 |
| Edges with a resolved endpoint | 262 with dangling | 163, none dangling |
| Runtime, 100-paper run | 273 s | 55 s |

## 5.4 Defect 2: a single null field discarding batches of fifty

### 5.4.1 Symptom

After the traversal rewrite, one test paper still returned zero forward
citations although OpenAlex reported 53 citing works.

### 5.4.2 Diagnosis

The mapping function read the venue as:

```python
data.get("primary_location", {}).get("source", {}).get("display_name")
```

OpenAlex returns `"primary_location": {"source": null}` for works with no
indexed venue. `dict.get(key, {})` returns the default only when the key is
*absent*; when the key is present with a null value it returns `None`, and the
chained call raises `AttributeError`.

Because the exception was caught around the *whole batch*, one malformed record
discarded the other forty-nine:

```
fetched 50 citing works
  primary_location.source is null : 23
  mapping each work individually  : ok=27  FAILED=23
  -> one bad record aborts the whole batch of 50
```

Twenty-three of fifty records had a null venue. This is not an edge case.

### 5.4.3 Resolution

Null-safe accessors, and a per-record `try`/`except` inside the batch loop so a
malformed record is skipped and logged rather than aborting its neighbours. The
same defect shape was found and fixed in the Crossref and Europe PMC mappers,
where it had not yet been triggered.

A secondary effect was discovered at the same time: because batch failures
forced a fallback to per-paper resolution, the run had been taking 209 s. After
the fix the same run took 12 s.

## 5.5 Defect 3: ignore rules discarding the numbers they protect

### 5.5.1 Symptom

Only 15% of papers in a typical graph received any population evidence.

### 5.5.2 Diagnosis

The extractor applied its ignore patterns, years, percentages, p-values,
dosages, at *sentence* granularity:

```python
for ignore_p in IGNORE_PATTERNS:
    if re.search(ignore_p, sentence):
        should_skip_sentence = True    # discards the entire sentence
```

`IGNORE_PATTERNS` includes `\b20\d{2}\b`, matching any year. Clinical abstracts
mention a year or a percentage in most sentences. The rule intended to prevent
"2019" being read as a sample size was discarding the sample sizes themselves:

```
DROPPED  PATIENTS_COUNT=1099 ('1099 patients')
         because the sentence also matched '\b20\d{2}\b'
```

The sentence was *"We extracted data regarding 1099 patients with
laboratory-confirmed Covid-19 from 552 hospitals ... through January 29,
2020."* The pattern matched the cohort size correctly and the extractor then
threw it away because of the date at the end of the sentence.

### 5.5.3 Resolution

Ignore patterns are now matched per *span*. A candidate is rejected only when
the captured number itself falls inside an ignored span. A year is still never
read as a population; a count standing beside a year survives.

Separately, the pattern set assumed randomised-trial phrasing. "We analyzed
data on the first 425 confirmed cases" matched nothing, because no pattern
covered *cases*. Patterns were added for the phrasings observational papers
use, *a total of N*, *N confirmed cases*, *N subjects*, *N consecutive
patients*, *included/recruited/studied N*, *data on N*, along with patterns for
`SCREENED`, `COMPLETERS`, `ARM_SIZE` and `FOLLOWUP_COUNT`, four semantic types
the model defined but which no pattern could previously emit.
| Measure (40-paper graph) | Before | After | |--------------------------|-------:|------:| | Papers with extracted evidence | 7 | 15 | | Of those with an abstract | 7/29 | 15/29 | | High confidence (≥ 0.8) | 3 | 10 |

## 5.6 Defect 4: edge weights collapsing to zero

### 5.6.1 Symptom

None. This defect produced no visible symptom, which is why it is the most
instructive in the catalogue.

### 5.6.2 Diagnosis

The original weighting multiplied the entire base weight by population
confidence. A resolution with status `missing` carries confidence 0.0 by
definition, so:

```
resolution with no candidates -> n_eff=None  confidence=0.0
  P1->P2  base=0.125  FINAL=0.0
  P1->P3  base=0.125  FINAL=0.0
  P2->P3  base=0.125  FINAL=0.0
```

Every edge weight was exactly zero for any paper where extraction found
nothing, which, before Defect 3 was fixed, was 85% of papers.

The ranking nonetheless produced sensible output, and this is why the fault
survived. The graph builder contained:

```python
weight=edge.final_weight or 1.0
```

In Python, `0.0 or 1.0` evaluates to `1.0`. Every zeroed weight was silently
replaced by 1.0, and PageRank ran **unweighted**. The system's central claim,
evidence-weighted citation analysis, was not operating, and the fallback that
concealed it was an accident of truthiness rather than a designed behaviour.

### 5.6.3 Resolution

Confidence now scales the evidential term only, as in Section 4.5. The builder
falls back only on a genuine `None`, so a real zero can no longer be disguised.

| Case | n_eff | confidence | final weight |
|------|------:|-----------:|-------------:|
| No evidence | n/a | 0.00 | 0.125 |
| Small trial | 120 | 0.85 | 0.391 |
| Large trial | 8,500 | 0.90 | 0.655 |
| Very large | 100,000 | 0.95 | 0.837 |
| Large, low confidence | 8,500 | 0.30 | 0.302 |

Evidence still outranks absence, larger samples outrank smaller, and low
confidence is penalised, but nothing collapses to zero.

## 5.7 Defect 5: server-Side request forgery in URL input

Accepting an article URL requires fetching it when no identifier can be parsed
from the URL text. The implementation fetched any URL that had a scheme and a
host, with redirects followed automatically.

Verified against a local listener:

```
PaperQuery ACCEPTS http://127.0.0.1:9911/internal/admin
PaperQuery ACCEPTS http://169.254.169.254/latest/meta-data/
listener received 1 request
resolver returned: query_type='title' value='Internal Service Banner v2.4'
```

The system could be directed at loopback, link-local (cloud metadata) or
private addresses, and the fetched page's `citation_title` was forwarded to
Crossref and Europe PMC as a search term, a narrow but real exfiltration
channel.

The resolver now rejects any URL whose host resolves to a private, loopback,
link-local, reserved, multicast or unspecified address, and follows redirects
manually so every hop is re-validated. A public host that redirects to an
internal one is refused at the second hop.

A separate URL defect was found in the same component: the DOI character class
includes `/`, so matching against a URL path ran past the end of the DOI into
the publisher's view segment, yielding `10.3389/fcomp.2024.1387354/full` and
failing the run. Trailing view segments are now trimmed.

## 5.8 Defect 6: exports returning JSON envelopes

The frontend saved export responses directly to disk as `citegraph-<id>.csv`,
but the backend returned `{"csv": "..."}`. Users received a `.csv` file
containing a JSON envelope with the whole table escaped onto one line.

All exports now return the file itself with the correct `Content-Type` and a
`Content-Disposition` filename. Both CSV exports are written with the `csv`
module, so a comma, quote or newline in a title or journal can no longer break
a row, the previous hand-rolled formatting never escaped the journal field at
all, and carry a UTF-8 byte-order mark so spreadsheet software renders accented
author names correctly. An edge-list export and a GraphML export were added;
the frontend had offered GraphML as a format although no such route existed.

## 5.9 Deployment

The backend runs as a Docker container bound to the loopback interface on a
shared host, behind nginx with a Let's Encrypt certificate. The frontend is a
static single-page application on a content delivery network. Cross-origin
access is restricted to the frontend origin; a wildcard policy was replaced
because it would allow any page a developer visits to drive a locally running
instance and read the responses.

An optional API-key gate exists but is unset in the current deployment, because
a public single-page application cannot hold a secret. This is recorded as an
open issue in Section 7.5 rather than presented as a completed control.

A defect in the deployment workflow is worth recording alongside the software
defects: the container publication directive was `-p "${PORT}:8000"`, which
binds `0.0.0.0` and would have exposed the API directly to the internet,
bypassing nginx and TLS, on a host shared with three other projects. It now
binds `127.0.0.1` explicitly and the deployment fails if the port is found on a
public interface.

## 5.10 Discussion: why these defects survived

Six defects reached a system that passed its tests, and four of them produced
output that looked correct. Three properties of the failures explain this.

**They failed silently.** The traversal defect logged at warning level and
continued. The `cites` filter defect returned HTTP 200. The weighting defect was
masked by a truthiness coincidence. None raised an error.

**They produced plausible output.** A graph with 19 nodes instead of 40 looks
like a sparse literature, not a bug. A ranking from unweighted PageRank is still
a ranking. Plausible-looking wrong output is harder to detect than a crash.

**The tests asserted shape, not correctness.** The suite verified that a run
completed and returned a structure with the right fields. No test asserted that
the number of nodes bore any relation to the number of references available, or
that edge weights varied.

The methodological conclusion is that for a system whose output is a ranked
list, correctness cannot be established by testing that the pipeline runs. It
requires measurement against known quantities, which is what Chapter 6 reports,
and what the project proposal had specified from the outset.
