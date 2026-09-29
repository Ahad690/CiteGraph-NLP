# Plan: apply the AnswerThis study to CiteGraph, and add typed LLM evaluation

Derived from reverse-engineering answerthis.io (two HAR captures + decoded bundle), plus a
decision to add two LLM-backed capabilities: **GLM-5.3-flash** for narrative report
generation, and **Jev (TypeSafe)** for typed probabilistic decisions.

Every item was checked against the CiteGraph codebase before being included. Items that
turned out to be non-transferable were dropped rather than dressed up. The provider
architecture follows the **`Terminux` project** at `C:\Users\subha\Documents\PROJECTS\Terminux`,
which already has a hardened multi-provider client and — critically — a `zai` provider entry
with a measured GLM usage-accounting trap documented (see 6.4).

## What the study taught, and what actually transfers

AnswerThis is a React + Vite + Zustand research assistant that resolves a question into a
job, polls a 202 → 200 lifecycle, and renders citations with CSL/citeproc. Four patterns
were examined against CiteGraph's own code:

| Pattern | Verdict for CiteGraph |
|---|---|
| HTTP status as terminator (`202` interim, `200` done) | **Already better.** `deriveStatus` types the body and defaults to `?? "started"`, so a malformed response cannot hang the poll. AnswerThis depends on the status code arriving. |
| 500 ms fixed polling | **Transferable.** CiteGraph hardcodes `refetchInterval: 2000`. AnswerThis returns `retry_after_ms` and the client obeys it. |
| CSL/citeproc citation rendering | **Transferable and missing.** `git grep` finds no citation formatting anywhere. Export is JSON/CSV/GraphML only. |
| Server-side vendor credential, `content_sha256` | **Transferable after all.** AnswerThis keeps its vendor token server-side behind `backend_jwt`. With two providers now, CiteGraph needs the same discipline. |
| Five analytics SDKs on an 11.4 MB bundle | **Anti-pattern, recorded not copied.** |

## The LLM addition, and why it changes the design

Both new capabilities sit in the same architectural slot, so one interface must serve both:

- **Jev** is not a chat model. It is a *typed decision* engine: `choice`, `score`, and
  `noul` questions answered with probability distributions and confidence. That maps
  exactly onto CiteGraph's existing problems — "is this a randomised trial or an
  observational one", "how confident is this link", "does this claim state a fact".
- **GLM-5.3-flash** is a conventional chat model, needed for the narrative report that
  the study showed is the product's most visible surface.

**The thesis already admits the weak point this fixes.** `06-evaluation-results.md` reports
distinguishing *randomised* from *enrolled* from *analysed* correctly in only 6 of 10 cases
(60%). A `choice` question against Jev is precisely that task, and it returns a
probability distribution rather than a bare label — which is what CiteGraph's provenance
story wants. This turns a published weakness into a measured improvement.

**The scope conflict to settle first.** `docs/plan-answerthis-lessons.md` previously
asserted "the product has no LLM". The thesis itself does not make that claim — it says
"rule-based" where accurate (`04b-algorithms.md:203`, `04b-algorithms.md:231`) — so the
change is compatible with the document as written, but Chapter 3, 4 and 7 all describe a
deterministic pipeline and will need updating. Phase 6 handles that.

---

## Phase 1 — Capture the study as a durable reference

**1.1** Move the two deliverables into the repo as a competitive reference.

- Source: `C:\Users\subha\Documents\Codex\2026-09-29\i-have-attahc\outputs\answerthis-study\`
- Destination: `docs/competitive/answerthis/`
- Files: `answerthis-architecture.md`, `answerthis-study-log.md`
- Include the HAR-derived facts only. No response bodies, no query or answer text, no
  credential values. Re-run the token/email/phone scan before committing; both files are
  currently clean.

**1.2** Add `docs/competitive/answerthis/README.md` stating provenance and standing:

- Captured 2026-09-29 against a user-owned throwaway account, two HAR exports.
- Six questions remain open; list them with what would settle each.
- Every claim is tagged *observed* / *inferred*. The two corrected errors stay visible:
  the false Vue fingerprint and the wrong "Preserve log" claim.

**1.3** Add a one-line note in `docs/competitive/answerthis/` that this is a client- and
traffic-level study. It says nothing about AnswerThis's retrieval stack, prompt design, or
evaluation. Without that caveat the document invites over-reading.

**Gate:** no credential-shaped string, no query text, no answer text in the committed tree.

---

## Phase 2 — Close the two untested load-bearing modules

This is first because it is real risk today, not a feature.

**2.1** `src/citegraph/evaluation/metrics.py` — 0/74 statements covered.

Corrected finding: all four functions **are** used in production, by
`scripts/run_evaluation.py`, and they produce the confidence intervals and
detection-accuracy figures the thesis quotes. This is untested code behind published
numbers. `wilson_interval` in particular is the kind of function that is wrong by a small
amount and nobody notices.

Tests to write in `tests/`:

- `wilson_interval` — zero trials, 100% success, 0% success, symmetry, widens as trials
  fall, and a hand-computed value at n=10/k=6 checked against the published formula.
- `exact_match_rate` — empty input, all match, none match, partial.
- `normalised_title_similarity` — identical, case and punctuation differences, empty/`None`
  on either side, genuinely different titles.
- `graph_connectivity` — single paper, no edges, a connected chain, a disconnected
  component, and empty inputs.

**2.2** `src/citegraph/graph/exporters.py` — 0/17 statements. `to_json`, `to_graphml`,
`save_all`. Cover round-tripping, empty graph, and that `save_all` writes every promised
file.

**2.3** Confirm the coverage ratchet actually moves. The CI floor is 72 against a measured
72.64 combined. Adding these tests should lift the measured figure; when it does, raise
`--cov-fail-under` to the new floor in the same commit. Never lower it.

**Gate:** `python -m pytest tests/ -q` green, coverage.xml regenerated, `check_coverage_report.py` passes.

---

## Phase 3 — Citation export via CSL/citeproc

**3.1** Decide the runtime. Citeproc is a mature JavaScript library, and the frontend
already has a toolchain. The backend is Python. Two routes:

- **3.1.a (recommended)** — a new `frontend/src/lib/cite.ts` using `citeproc`, invoked from
  the export page, producing BibTeX and RIS client-side. No new backend, no Python port of
  citeproc to maintain, and it matches how AnswerThis does it.
- **3.1.b** — a Python implementation. Larger, and citeproc's Python options are weaker.
  Choose only if exports must be server-side for a reason not yet identified.

**3.2** Assemble CSL input from `RunResult`. Map CiteGraph's fields to CSL variables:
`title`, `author` (the alias table already resolves author identity), `issued`,
`container-title`, `DOI`, `URL`, `type`. Anything absent stays absent rather than being
invented — citeproc renders around missing fields, and fabricating a date to fill a
template would corrupt every downstream citation.

**3.3** Ship two formats and two styles to prove the point:

- Formats: **BibTeX** and **RIS**
- Styles: **APA 7th** and **IEEE**, fetched as CSL JSON (AnswerThis fetches from
  `apastyle.apa.org`; vendor them locally so an export never depends on a network call)

Shipping a local CSL style directory is the transferable idea: **style becomes data, so
adding Chicago is a file drop, not a code change.**

**3.4** Expose it in the existing export surface: `frontend/src/routes/export.$runId.tsx`
gains a citation section alongside the existing JSON, CSV, and GraphML downloads.

**3.5** Decide and record the provenance question. CiteGraph's whole argument is that every
citation carries a link-confidence score. A BibTeX file has nowhere to put that. Options:
a comment field, a `note`, or nothing. **Recommended:** a `note` on entries below a
confidence threshold, because silently exporting a low-confidence link as if it were
settled is exactly the failure the provenance design exists to prevent.

**3.6** Tests: golden-file comparison against known BibTeX and RIS output for a fixed
`RunResult`; a missing-field case; a low-confidence case proving the note appears.

**Gate:** a real run exports BibTeX and RIS that open in a reference manager, with a test
proving the output.

---

## Phase 4 — Two polling improvements from the study

**4.1** Server-driven poll interval.

`POST /runs` and `GET /runs/{run_id}` gain a `retry_after_ms` field alongside `status`,
mirroring the one pattern where AnswerThis is better designed. `useRun.ts` stops
hardcoding `2000` and honours it, with the current value as the default when absent.

Small change, honest provenance: this is the single place their design is better, and the
reason is that a client cannot know whether the server is under load.

**4.2** Test the response-shape contract, since it is the thing that actually protects the poll.

- A `RunResult` body with no `status` field derives `"completed"`.
- A malformed partial body does **not** derive `"completed"` — this is the case where a
  naive `if (papers.length)` would wrongly stop polling, and the existing code comment says
  so explicitly.
- A `RunStatusPayload` with an unknown status keeps polling rather than throwing.
- `pending` and `processing` are in `POLL_STATUSES` but the backend never emits them
  (verified: no match anywhere in `src/`). Decide whether they are legacy tolerance worth
  keeping, and write the test that documents the decision either way.

**Gate:** the poll cannot be made to hang or to stop early by a malformed response, proven
by test.

---

## Phase 5 — Thesis write-up

The supervisor will ask why these choices were made. Record that, in the thesis, not only
in a commit message.

**5.1** Chapter 4 (design), where export and the run lifecycle belong:

- Why the poll derives from a typed body rather than a status code, with the
  malformed-response argument. This is a **defence**, because AnswerThis made the opposite
  choice and a reviewer who knows the alternative will ask.
- Why citation export uses CSL, and why styles are vendored rather than fetched.

**5.2** Chapter 7 (discussion), competitive positioning:

- CiteGraph against AnswerThis on the three axes the study actually measured: provenance
  and confidence, citation handling, and the run lifecycle. CiteGraph wins on provenance
  and lifecycle; loses on citation export until Phase 3 lands. Say so plainly.
- What was deliberately **not** copied, and why: no LLM in the product, one client state
  library, no analytics sprawl, and a bundle an order of magnitude smaller.

**5.3** Chapter 6 (evaluation), after Phase 2:

- The confidence intervals now have tests behind them. Note it, briefly, where the numbers
  are first introduced.

**5.4** Re-run the drift guard after every thesis edit. `python scripts/build_thesis.py`,
then `render_thesis.py`, then `pytest tests/test_the_thesis_does_not_drift.py`. The
baseline tracks 265 sections, 9 figures, and 48 citations, and it fails if any disappears.

**Gate:** drift guard green, 126 pages, 19 passed / 1 skipped.

---

## Decisions needed before starting

1. **3.1.a or 3.1.b** — client-side citeproc (recommended) or a Python implementation.
2. **3.5** — whether low-confidence citations carry a `note` into BibTeX (recommended) or
   are exported silently.
3. **6.2** — whether Jev runs always-on, or only below a confidence threshold with the
   existing rules as the fast path (recommended). Cost and latency differ materially.

---

## Phase 6 — Typed LLM evaluation: Jev and GLM

Follows the Terminux provider pattern: `src/citegraph/llm/` with `base.py`, `jev.py`,
`glm.py`, `transport.py`, `usage.py`, mirroring `Terminux/src/terminux/provider/`.

### 6.1 Credentials — read the key, never the file

The key is at `C:\Users\subha\Downloads\glm_API_key_for_glm-5.3-flash.txt` (49 bytes, one
line). **Contents have not been read and will not be printed, logged, or echoed.**
- A one-time copy into `CITEGRAPH_PROJECTS/CiteGraph-NLP/.env` as `GLM_API_KEY=...`, using a
  script that reads the file and writes the assignment without ever returning the value to
  stdout. Delete the Downloads copy afterwards if the user confirms it is no longer needed.
- `TYPESAFE_API_KEY` for Jev, same route. No Typesafe key file has been provided; the user
  must supply one before Phase 6.2.
- Confirm `.env` is git-ignored. It is not currently in `.gitignore` — **add it**, alongside
  the existing `docs/proposal/` rule.
- Reuse CiteGraph's existing `pydantic-settings` `config.settings` so both keys load through
  one path, and so a missing key is refused at boot rather than at first call. Terminux has
  `test_boot_checks_the_configuration_it_has.py`; the equivalent test belongs here.

### 6.2 `llm/base.py` — one interface, two providers

A `Provider` protocol with `evaluate(request) -> ProviderResponse`, plus a registry that
resolves by name. Both providers implement it; the caller never branches on vendor.

- **Jev** is not a chat model. Do **not** route it through a `/chat/completions` shape. Its
  surface is `POST /v1/systemone` with `state` plus a `questions` map, returning
  `answers.{id}` with a probability distribution, confidence, and `usage`.
- Implement **choice**, **score**, and **noul** question types with the exact response
  shapes: `choice` returns a selected key plus per-criterion probabilities; `score` returns
  a zero-based index into the ordered criteria plus a distribution; `noul` returns a
  probability in `[0,1]`.
- Multiple questions per request, sharing one `state`. Jev is built to evaluate several
  decisions against the same input, and batching is where the latency win is.
- Ergonomic helpers `choice()`, `score()`, `noul()` mirroring the API's own shape.

**Threshold policy is application-level, not global.** Per the specification, do not
hard-code 0.7 anywhere shared. CiteGraph's own thresholds belong to the call site that
knows what a wrong answer costs. A mis-scoped trial type should be flagged for review, not
silently accepted and not silently dropped.

**Log the returned `model` on every call.** The specification requires this for
reproducibility, and CiteGraph's drift guard makes it doubly necessary: a thesis number
must be attributable to the exact model version that produced it, and `jev-latest` will
move under it.

### 6.3 `llm/transport.py` — the socket, with the traps written down

Copy the discipline from `Terminux/src/terminux/provider/transport.py`, whose docstring
records four wire-level behaviours that only appear on a real connection. The Terminux
ones that apply here:

- **An error can arrive with HTTP 200.** Once a stream is open the status is already sent.
  A client checking only `status_code` reads a provider failure as an empty success.
- **`finish_reason` arrives before the usage chunk.** Stopping there loses the usage record
  that billing depends on. Run to `[DONE]`.
- **A stalled stream is not a closed stream.** Needs a gap watchdog re-armed per chunk, not
  a total-request timeout.
- **Keepalive comments are not JSON.** OpenRouter emits `: PROCESSING` lines.

Error handling, per the Jev specification:

| Status | Behaviour |
|---|---|
| 401 | Auth failure. **No retry.** Never log the key. |
| 422 | Schema error. **No retry.** Return the validation detail. |
| 429 | Retry with exponential backoff, honour `Retry-After`. |
| 529 | Overloaded. Retry with backoff. |
| — | Connection errors, timeout, invalid JSON, malformed response. |

Backoff 1s / 2s / 4s **with jitter**, max retries configurable, ~10s default timeout. Ordinary
4xx never retried.

### 6.4 `llm/usage.py` — and the measured GLM trap

Terminus already documents this, so cite it rather than rediscovering it:

> *"GLM does not expose `prompt_cache_hit_tokens` at all; reading that name against it would
> have reported 0% on every turn while being billed for ~97%."*

Cache accounting is **not** interchangeable across providers. DeepSeek's hit and miss tokens
are mutually exclusive and sum to the total; OpenAI's `cached_tokens` is *inclusive*; GLM
exposes neither field name. Summing naively silently corrupts cost estimates while the
numbers still look plausible.

- Track token usage and cost per call, per provider.
- When a provider omits a breakdown, fall back **conservatively to all-miss**, so CiteGraph
  over-estimates its own cost rather than under.
- An unrecognised provider shape is a shape that has not been checked — not one to assume.
- Caching keyed by content hash, so re-reading the same paper never re-bills. Worth it for
  GLM specifically, because classification is deterministic-shaped work that will repeat.

### 6.5 Wire the two capabilities

- **Jev → the 60% weakness.** Replace the rule-based randomised/enrolled/analysed
  disambiguation in `src/citegraph/nlp/population_extractor.py` with a `choice` question, and
  keep the distribution rather than collapsing to a label. Anything below the threshold falls
  back to the existing rule and is flagged, so behaviour degrades to today's rather than
  breaking.
- **Jev → link confidence.** `score` questions over the existing linkage features
  (`graph/weighting.py`) give an ordered confidence instead of a bare number, feeding the
  `confidence` column the thesis already reports.
- **GLM → narrative report.** Generate a literature-review-style summary from the citation
  graph, with every claim carrying its source paper and link confidence. **No claim the
  graph cannot support.** The provenance design means a generated sentence with no supporting
  edge is a defect, not a stylistic problem.

Both calls are server-side. The browser never receives either key.

### 6.6 Tests — no live API calls

Mock the transport. Cover, following the specification: choice, score, noul, and multiple
questions request/response shapes; 401 no-retry; 422 no-retry; 429 retry then success; 529
retry; timeout; malformed response; invalid JSON; retry-after jitter present; the
never-log-the-key invariant; and a test that a missing `TYPESAFE_API_KEY` refuses at boot.

Add a guard that fails if either key appears in a log line, an exception message, or a
serialised response. Terminux's `src/gate_runner/secrets/scan.py` is the reference.

### 6.7 What this does not do

No chat UI. Jev is not a chat model and is not wrapped as one. No provider switching mid-run
— pin per run and log the model version, because a reproducibility claim that cannot name
its model is not a claim.

---

## Sequencing and risk

| Phase | Depends on | Risk | Reversible |
|---|---|---|---|
| 1 Reference | — | none | yes |
| 2 Coverage | — | none; tests only | yes |
| 3 Citation export | 3.1 decision | **medium** — new dependency, output correctness | yes, additive |
| 4 Polling | Phase 2 complete | low | yes |
| 6 LLM clients | 6.1 keys, `TYPESAFE_API_KEY` | **high** — live vendor calls, cost, a new failure mode in the pipeline | yes, additive |
| 6.5 Wire in | 6.2–6.4 | **high** — changes a published 60% number | yes, behind a flag |
| 5 Thesis | 2, 3, 4, 6 | low, but the guard is strict | guard-mediated |

Phases 3 and 6 are the two that can reach a user. Phase 6 carries the most risk because it
introduces a **network-dependent, cost-bearing, non-deterministic step into a pipeline whose
entire argument is determinism and traceability**. Two mitigations, both mandatory:

- **Every provider call sits behind a feature flag and a cache.** A run with the flag off
  behaves exactly as it does today, so the deterministic path stays demonstrable.
- **The drift guard must record the model version** behind any published number. A thesis
  claim that cannot name the model that produced it is not reproducible.

## Decisions needed before starting

1. **3.1.a or 3.1.b** — client-side citeproc (recommended) or a Python implementation.
2. **3.5** — whether low-confidence citations carry a `note` into BibTeX (recommended) or
   are exported silently.
3. **6.2** — whether Jev runs always-on, or only below a confidence threshold with the
   existing rules as the fast path (recommended). Cost and latency differ materially.
4. **`TYPESAFE_API_KEY`** — needed before Phase 6.2. No key file has been supplied.
5. **Budget ceiling** — a hard spend cap for provider calls per run and per day. Without one,
   a retry loop on a 429 is an unbounded bill.

## What this plan does not do

- It does not chase the six remaining open questions. They concern AnswerThis's internals
  and would not change a single line of CiteGraph.
- It does not add a chat interface. Jev is a typed decision engine and is not wrapped as a
  chat model.
- It does not put either vendor key in the browser, in git, or in a log line.
- It does not let a generated claim enter a report without a supporting graph edge. The
  provenance design is the product; a fluent sentence with no citation is a regression
  against it, however good the prose.
- It does not treat the study as a benchmark. It is a client-and-traffic observation of one
  product on one day, and Chapter 7 must not overstate it.
