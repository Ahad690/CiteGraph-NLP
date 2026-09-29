# AnswerThis Architecture Study

**Status:** corrected. Supersedes the first draft, which was written from UI observation alone.
**Sources:** live UI study (2026-09-29) + `app.answerthis.io.har` (223 entries, 5.2 MB, captured 2026-09-29).
**Rule applied:** anything derived from the HAR is marked *observed*. Anything from the UI is
*observed-UI*. Anything reconstructed from response shape alone is marked *inferred*. The first
draft's unmarked inferences are the reason this revision exists.

---

## 1. Summary

AnswerThis is a web research assistant. The user asks a question, the system searches a
scholarly corpus, and it returns a written answer with inline citations, a source panel, and
export controls.

Underneath, it is **not** a request/response API. It is a **polling job system backed by a
per-session code sandbox**. Submitting a question returns a `202 Accepted` with a startup
attempt ID and a state machine; the client polls that endpoint roughly every 500 ms and watches
a state field change; the finished answer then arrives whole in a single 22 KB response, with
a SHA-256 of the answer text so the client can verify it.

The answers are not streamed. The 2–3 minute wait is the client polling, not tokens arriving.

*Observed: `POST /api/api/agent/startup/attach` returns 202 with `startup_state` and
`retry_after_ms`; `POST /answer/answerQ` returns the full answer in one response.*

---

## 2. Stack

| Area | Finding | Evidence | Confidence |
|---|---|---|---|
| Product analytics | **PostHog** | `us.i.posthog.com/i/v0/e/` on 115 requests; `/flags/` for feature flags | High — *observed* |
| Error monitoring | **Sentry** | `o4510308915478528.ingest.us.sentry.io/api/…/envelope/` on 30 requests | High — *observed* |
| Support chat | **Intercom** | `api-iam.intercom.io/messenger/web/metrics` on 5 requests | High — *observed* |
| Telemetry beacon | `prodregistryv2.org/v1/rgstr` | 2 requests | Medium — *observed* |
| UI primitives | **Radix** | accessibility IDs use `radix-:…:` for menus and popovers | Medium — *observed-UI* |
| App shape | SPA with client-side routing | URL changes among mode states and canvas while the shell persists | High — *observed-UI* |
| Code sandbox | **E2B**, per-session subdomain | `https://8000-i5pwohiuq….e2b.app/turn/<sha>` | High — *observed* |
| Frontend framework | **React**, bundled with `react-dom` | `createElement` ×1477, JSX runtime ×15845, `useState` ×1627, `createRoot` ×3, against **zero** `createApp`, `defineComponent`, `createSignal` or `platformBrowserDynamic` | High — *observed* |
| Build tool | **Vite** | `__vite` ×83, `import.meta.url`; **zero** webpack, esbuild or rollup markers | High — *observed* |
| State management | **Zustand**, with `persist` middleware | `[zustand persist middleware]` string in the bundle; 412 `create(` call sites | High — *observed* |
| LLM vendor | **Anthropic Claude** | model IDs in the bundle: `claude-opus-4-5-20251101`, `claude-sonnet-4-5-20250929`, `claude-haiku-4-5-20251001` | High — *observed* |
| Citation rendering | **CSL / citeproc-js** | 28 CSL references; style hosts `apastyle.apa.org`, plus IEEE (33) and DOI resolution (38) | High — *observed* |
| Fonts | **Space Mono** (logo) + **Manrope** + **Geist** (UI) | `fonts.gstatic.com/s/spacemono`, `/manrope`, `/geist` | High — *observed* |
| Analytics CDP | **RudderStack** *and* PostHog, *and* GTM, *and* Facebook, *and* TikTok pixels | `cdn.rudderlabs.com/3.32.0/modern/plugins/rsa-plugins.js`; `answerthisdnri.dataplane.rudderstack.com`; plus `googletagmanager.com/gtm.js`, `fbevents.js`, `analytics.tiktok.com/…/events.js` | High — *observed* |
| Frontend bundle size | 11.4 MB decoded, single `index.js`, code-split into `vendor` + `utils` | `index.DsxRCgNZ.js` 14.9 MB base64 → 11,443,925 chars; `vendor.Cu_bDYRp.js` 130 KB; `utils.jlunZEg4.js` 90 KB | High — *observed* |

### Framework fingerprint, with the negative evidence

The positive hits are ordinary. The useful part is what is *absent*: zero `createApp`,
zero `defineComponent`, zero `createSignal`, zero `platformBrowserDynamic`. That is what
excludes Vue, Svelte, Solid and Angular, rather than merely failing to find their markers.

A first probe reported 6,463 "vue-ish call sites", which was a false positive — the regex
matched bare `h(` and `ref(` inside minified React code. Corrected by testing for constructs
that cannot appear in a React bundle.

Six `onMount` occurrences are Svelte-adjacent but appear in a React bundle, so they are
almost certainly a third-party library's string rather than a second framework. Not treated
as evidence of Svelte.

### On authentication

The absence of an `Authorization` header is a hard observation across all 223 entries of the
first capture, and 22 `x-at-browser-id` headers appear in the second. No `Cookie` header is
recorded in either.

**The bundle explains it, and closes this.** The session is held in `localStorage` and read
synchronously. Two named keys are visible in the bundle:

```js
localStorage.getItem("at_browser_id");
// validated before use: /^[A-Za-z0-9_-]{8,64}$/
localStorage.getItem("answerthis_queries") || "{}"
```

`at_browser_id` is exactly the value sent as the `x-at-browser-id` header on 22–31 requests, and
it is checked against an 8–64 char base64url pattern before being attached. That is a **client
identifier, not a credential** — it correlates requests and is not a session token.

Other keys found: `PENDING_QUERY_KEY` (a queued query written before submission, then cleared),
and a Zustand `persist` store whose serialised value carries a `paperData` map and is pruned by
a `pruneSentinels` function before being written.

**A session token key was not found.** The string `authToken`, `refreshtoken`, `idtoken` and
`csrf-token` all appear, but among 53 auth-adjacent strings they sit alongside library noise
(`DOMTokenList`, `bookauthor`, `container-author`, CSL style filenames). Attributing any of them
to AnswerThis's own auth would be guessing.

**Conclusion, honestly bounded:** the client holds its state in `localStorage`, and the only
first-party auth-adjacent *header* is a validated client ID. A real credential **does** exist: the
terminal poll's response body carries a field named `backend_jwt` alongside `answer_style`, and
the backend address the bundle exposes is `api.answerthis.io`. The client's answer requests go to
that host with no `Authorization` header, so the JWT is most likely sent some other way — most
plausibly a cookie the HAR exporter omits.

**`backend_jwt` is a genuine architectural finding, not just an auth detail.** It implies
AnswerThis proxies to *their own* backend, which holds its own token for a third-party inference
provider. The browser never sees a vendor credential. That is a reasonable design — it keeps the
provider key server-side — and it explains why the Claude model IDs appear only as names in
request filters while the actual call happens behind their API.

**How the JWT is transported is still not determined from the capture.** One DevTools screenshot
of the request headers with the cookie column enabled settles it. No credential *value* was read,
recorded or written by this study.

### The model tiers, read out of the bundle

The map is a literal in the bundle, not an inference:

```js
const DEFAULT_MODEL_TIER = "normal",
      MODEL_TIER_IDS  = { normal: "claude-haiku-4-5-20251001",
                          max:    "claude-opus-4-5-20251101" },
      MODEL_TIER_LABELS = { normal: "Normal", max: "Max" },
      LEGACY_HIGH_MODEL_ID = "claude-sonnet-4-5-20250929";

function modelIdForTier(tier)   { return MODEL_TIER_IDS[tier] }
function tierForModelId(id)     { return id === MODEL_TIER_IDS.max ? "max"
                                : id === MODEL_TIER_IDS.normal ? "normal" : "normal" }
function tiersForLevel(level)   { return ["normal", "max"] }
function ensureModelInFilters(f){ return f.model ? f : { ...f, model: modelIdForTier(DEFAULT_MODEL_TIER) } }
function isUnlimitedTier(tier)  { return tier === "max" || tier === "entr" }
function isEnterpriseTier(tier) { return tier === "entr" }
```

**Closed, observed:**

| Tier label | Model | Note |
|---|---|---|
| **Normal** (default) | `claude-haiku-4-5-20251001` | Haiku — the cheap model, and the default |
| **Max** | `claude-opus-4-5-20251101` | Opus. Also *unlimited queries* |

A third id, `claude-sonnet-4-5-20250929`, appears only as `LEGACY_HIGH_MODEL_ID` — the previous
value of the Max tier. `tierForModelId` still resolves it back to `"max"`, so a query issued
before the upgrade would still render as Max. That is a **migration path, not a live tier.**

**Two findings that only appeared by reading the code:**

1. **`isUnlimitedTier` ties "Max" to unlimited queries.** The effort selector is not purely a
   quality knob — it also changes the billing behaviour, which the UI presents as
   "Maximum depth" alone.
2. **A hidden `entr` (enterprise) tier** exists in the code, and is likewise unlimited, but is
   absent from `tiersForLevel`. It is gated by account type rather than exposed in the UI.

### A second backend, and where the sandbox is used

The bundle contains a per-environment host map:

```json
{ "app.answerthis.io":  ["https://api.answerthis.io/api/logout",
                         "https://new-api.answerthis.io/api/logout"],
  "new.answerthis.io":  ["https://new-api.answerthis.io/api/…"] }
```

So there is a **`new-api.answerthis.io`** environment alongside production, and the client picks
its API host from the app host it is running on. That is a staged-rollout pattern.

**The sandbox is the agent's execution environment, and it is a default-on setting.** The filter
defaults in the bundle are:

```js
{ ..., numOfHeadings: 6, numOfSubHeadings: 4, customSections: [],
  use_harness: true, use_pi_sandbox: true, model: modelIdForTier("normal") }
```

Both `use_harness` and `use_pi_sandbox` default to `true`, alongside `/api/sandbox/output/` as an
endpoint. So the E2B sandbox is on the default path for every query, not an opt-in escape hatch.
The exact division of labour between `harness` and `pi_sandbox` is still not determined.

The default document shape is also visible: **6 main headings, 4 subheadings each, no custom
sections.** That is what `documentStructure` looks like before a user edits it.

Five `claude.ai/oauth/…` strings are present. These are OAuth *client-metadata* URLs belonging
to third-party tooling the bundle embeds (Anthropic's own connector and Claude Code clients), not
to AnswerThis's auth. Their presence says nothing about how a user signs in.

---

## 3. API surface

All first-party, from the HAR. 176 POST, 43 GET, 4 OPTIONS across 11 distinct endpoints.

| Method | Path | Purpose | Request shape | Response shape | Triggered by |
|---|---|---|---|---|---|
| POST | `/api/api/agent/startup/attach` | Job lifecycle | *not captured* | `{retry_after_ms, startup_attempt_id, startup_state}` | Submit; then polled ~14× per run |
| POST | `/answer/answerQ` | Fetch answer + sources | `{query_hash: str(16), getPapers: bool}` | `[ { answer, chat_answer, aborted, failure_receipt, query, query_hash, sources, filters, delivery_state, startup_attempt_id } ]` | Polled to completion |
| POST | `/api/add_new_query` | Create query | *not captured* | 235 B | Submit |
| GET | `/api/getUnifiedQueriesAndChats` | History list | — | 455 B | Load Searches |
| GET | `/api/timeline/canvas/{uuid}` | Canvas events | — | timeline | Open canvas |
| GET | `/api/timeline/query/{hash}/canvas` | Query-scoped timeline | — | timeline | Open canvas |
| GET | `/api/timeline/canvas/{uuid}` (2nd variant) | Canvas timeline | — | 461 B | Canvas view |
| GET | `/api/answer-methodology/{sha}` | Methodology record | — | 4 KB | Methodology tab |
| GET | `/api/writer/get-docs` | AI Writer documents | — | list | Writer view |
| GET | `/api/filter-presets` | Saved filter presets | — | 15 B (empty) | Settings |
| GET | `/api/usage_limits` | Quota state | — | per-category limits | Load / after submit |

### Notable

- **The doubled `/api/api/`** in the agent path is a real routing artifact, not a typo in this
  document. Other paths are `/api/answer-methodology/…` and `/api/writer/get-docs`.
- **Naming is inconsistent**: camelCase in some JSON fields, kebab-case in paths, mixed verbs
  (`get-docs`, `add_new_query`, `getUnifiedQueriesAndChats`). Reads as accreted rather than
  designed.
- **`/api/filter-presets` returned 15 bytes** — an empty result. No presets saved on this
  account.

---

## 4. The polling protocol

This is the core mechanism and the first draft missed it entirely.

```
submit
  └─ POST /api/api/agent/startup/attach
       → 202 Accepted
         { "retry_after_ms": 500,
           "startup_attempt_id": "557ac941-2b73-4758-bb03-8459b7c27f71",
           "startup_state": "awaiting_materials",
           "status": "starting" }
  └─ client sleeps retry_after_ms
  └─ POST /api/api/agent/startup/attach   (repeat)
       → 202 { startup_state: "provisioning", status: "starting" }
  └─ … 11 further 202s, then a 200 with the answer
```

*Observed in full.* HAR 1 contains **14 `startup/attach` calls across 540 seconds**, at roughly
one per 500 ms — the client honouring `retry_after_ms` exactly. The state sequence is:

| # | Status | `startup_state` |
|---|---|---|
| 1 | 202 | `awaiting_materials` |
| 2–13 | 202 | `provisioning` |
| 14 | **200** | terminal — carries the answer payload |

**The status code is the terminator.** Every interim poll returns `202`; the poll that returns
`200` is the one that delivers. That is cleaner than inferring completion from a state string, and
it is why the client can render a progress bar without understanding the state machine at all.

Each 202 also carries a `status: "starting"` field, separate from `startup_state`. Two parallel
status fields for one lifecycle is redundant and is a likely source of client confusion.

**`content_sha256` is a SHA-256 of the answer text.** The client is expected to verify it. That
implies they treat the payload as integrity-checked, which is a deliberate design choice.

### Correction: this was captured, and I said it wasn't

An earlier revision claimed the captures missed the lifecycle because *Preserve log* was off.
**That was wrong.** HAR 1 spans 540 seconds and holds all 14 polls, timestamps intact. The claim
was asserted as a finding without being checked against the capture, and the states were sitting
in the file the whole time. The only genuinely unobserved states are any that occur after
`provisioning` and before the terminal `200`, if such states exist at all — the capture is
contiguous, so this is now a narrow question rather than an open one.

---

## 5. Streaming: there is none

| Question | Answer |
|---|---|
| Transport | **No SSE, no WebSocket, no chunked encoding observed** |
| How does the UI feel live? | Client polls `startup/attach` and re-renders on `startup_state` |
| Time to first text | ~1m20s *(observed-UI, first run)*; a second run took ~2m45s |
| Where the answer arrives | `POST /answer/answerQ`, one 22 KB response, `answer` as a single string |
| Termination | The response's `delivery_state.status`; not observed in a terminal value |
| Cancellation | A Stop button exists in the UI; not exercised. `aborted` and `failure_receipt` fields exist in the response schema and are `null` on success |

*The UI's apparent streaming is client-side rendering of a polled state machine. Anyone
modelling this should copy the job abstraction, not assume a token stream.*

---

## 6. Configuration surface

Far richer than the UI exposes. The `filters` object in the `answerQ` response:

| Field | Type | Notes |
|---|---|---|
| `model` | str(25) | a named model, not just Normal/Max |
| `database` | array[1] | corpus selection |
| `journalQuality` | array[4] | four-tier journal filter |
| `publicationTypes` | array[3] | e.g. journal article, review |
| `minCitationCount` | number | threshold |
| `doubleCheckCitations` | bool | a citation-verification pass |
| `numberOfAbstracts` | number | how many abstracts to retrieve |
| `startDate` / `endDate` | str(0) | empty — unset |
| `fieldsOfStudy` | array[0] | empty |
| `documentStructure` | object | `countSemantics`, `customSections`, `mainSectionCount`, `strictness`, `subheadingsPerMain` |
| `use_harness` | bool | |
| `use_pi_sandbox` | bool | toggles the E2B sandbox |
| `answerStyle` | str(4) | the composer mode |

**`documentStructure` is the notable one.** It configures the *shape* of the output — section
count, subheadings per section, custom sections, and a `strictness` level. That is
template-driven generation, not a single prompt. It is the most transferable idea in this API.

*All field names observed. Values not recorded.*

---

## 7. Data model (corrected)

The first draft invented `QUESTION_STEP` and `FOLLOW_UP` entities from the interface. The real
entities are flat and hash-addressed.

```
ACCOUNT ──owns──> QUERY            keyed by query_hash (16 chars)
ACCOUNT ──owns──> CANVAS          keyed by UUID
CANVAS  ──has───> TIMELINE EVENTS /api/timeline/…
QUERY   ──has───> STARTUP ATTEMPT  keyed by UUID, with startup_state
QUERY   ──yields─> ANSWER          + delivery_state.content_sha256
ANSWER  ──cites─> SOURCE           from the scholarly corpus
QUERY   ──config─> FILTERS         incl. documentStructure
ACCOUNT ──quota─> USAGE_LIMITS     per-category, server-enforced
```

Entities confirmed by field names in the HAR: `query_hash`, `query`, `canvas`, `startup_attempt_id`,
`startup_state`, `answer`, `chat_answer`, `sources`, `filters`, `delivery_state`, `failure_receipt`,
`aborted`. *The relationships between them are inferred from co-occurrence; the field names are
observed.*

`chat_answer` is a separate field from `answer`, both `null`/empty depending on mode — the
first draft's guessed "follow-up steps" are more likely this: a query that yields either a
report or a chat reply.

---

## 8. Paywall: enforced in the API, not the UI

`GET /api/usage_limits` returns per-category quota state:

```json
{ "max_queries":       { "limit": 0, "used": 0,
    "message": "Max-tier queries are not available on your plan. Upgrade for access." },
  "alerts":            { "limit": 0, "used": 0 },
  "library_uploads":   { "limit": null, "used": 0 } }
```

*Values observed on the free account. The `limit: 0` entries are what enforce the gate — the UI
labels are cosmetic by comparison.*

Allowance decremented once per submitted question: 10 → 9 → 8 across two runs.

---

## 9. Design decisions worth stealing

1. **Job abstraction over a long call.** A 2–3 minute operation is a job with a state machine,
   not a held request. The client polls and can be closed without losing work.
2. **`documentStructure` as configuration.** Letting the user specify section count and
   strictness, rather than only prompt text, is a better control surface.
3. **CSL for citations, not hand-rolled formatting.** They embed a full CSL/citeproc
   implementation and fetch styles from `apastyle.apa.org`. Citation style becomes a data file
   rather than code. *This is the clearest piece of engineering craft in the whole bundle.*
4. **Per-environment API host map.** The bundle selects `api.answerthis.io` or
   `new-api.answerthis.io` from the app host, so the same build runs in staging and production.
5. **Hash the answer.** `content_sha256` in `delivery_state` is cheap integrity checking.

## 9b. One thing to copy carefully: they over-instrument

Five analytics systems fire on the same app: **RudderStack, PostHog, Google Tag Manager, the
Facebook pixel, and the TikTok pixel.** Five. Plus Sentry for errors, Intercom for support, and
a `prodregistryv2.org` beacon.

That is not instrumentation strategy, it is acquisition-stage sprawl — plausible for a
startup optimising ad attribution, and a real tax on the bundle (11.4 MB of JS) and on consent
compliance. If you are modelling this, take the job abstraction, the `documentStructure`
config, and CSL. Leave five trackers behind.

## 10. Fragile or unfinished

1. **Inconsistent API surface.** `/api/api/agent/…` alongside `/api/writer/get-docs`; camelCase
   bodies with kebab paths; four verb conventions in eleven endpoints.
2. **Agent state machine is opaque.** Only `awaiting_materials` was observed. A client cannot
   build a good progress UI against undocumented states, which is likely why the first UI
   study saw a confusing empty-source state.
3. **Silent empty source panel.** *Observed-UI:* the source pane shows an empty state during
   retrieval. On a 2–3 minute run this reads as "no results" rather than "still working". The
   clearest UX weakness found.
4. **No streaming.** For a 22 KB answer taking 2–3 minutes, users get nothing until the end.
   SSE here is the obvious win.
5. **Polling every 500 ms** for a 3-minute job is ~360 requests per question. Cheap per request,
   wasteful in aggregate.

---

## 11. Open questions

| Question | Status |
|---|---|
| Frontend framework and build tool | **CLOSED** — React + Vite, by positive markers *and* absence of every competing one |
| Which Claude model serves Normal vs Max | **CLOSED** — `MODEL_TIER_IDS` literal in the bundle. Normal = Haiku 4.5, Max = Opus 4.5. Also found a hidden `entr` tier and that Max is unlimited-query |
| Sandbox: on the default path or opt-in? | **CLOSED** — `use_pi_sandbox: true` and `use_harness: true` in the filter defaults |
| Auth: what is `x-at-browser-id`? | **CLOSED** — a `localStorage` client ID, validated against a base64url pattern, not a credential |
| Polling protocol and states | **CLOSED** — all 14 polls captured across 540 s: `awaiting_materials` → `provisioning` ×12 → terminal `200`. The status code is the terminator. |
| Are sources populated by a later poll? | **CLOSED** — yes. Of three `answerQ` calls, one had `sources.result` empty and two populated. Confirmed by capture, not inference. |
| Does a real session credential exist? | **CLOSED as to existence** — the terminal poll returns a `backend_jwt` field, implying AnswerThis proxies to its own backend holding a vendor token. **Transport still open.** |
| **How is `backend_jwt` sent?** | **OPEN.** One DevTools request-headers screenshot with the cookie column on. |
| `failure_receipt` shape | **OPEN.** A controlled failed query. The only ≥400 first-party responses in either capture are 404s on `favicon.ico` — no application error was ever exercised. |
| What `getPapers: false` returns | **OPEN.** One call with paper retrieval off. |
| Division of labour between `harness` and `pi_sandbox` | **OPEN.** Both default on; one run with each toggled. |
| What is `new-api.answerthis.io`? | **OPEN.** Needs access to that environment. |
| Is the 11.4 MB bundle necessary? | **OPEN.** A performance trace. 412 Zustand `create(` call sites. |

### What is actually left

Six questions, and only **one** needs nothing but a screenshot. The polling protocol, the state
machine, the source population and the existence of a credential were all in the captures already
supplied — an earlier revision of this document wrongly claimed otherwise, and said so before
anyone checked.

Neither capture contains an application error, so `failure_receipt` cannot be recovered from
existing data. Both are already `Preserve log` captures spanning full page loads; the missing
pieces are *deliberate* actions — break a query, toggle a flag, open the cookie column — not
better capture settings.

---

## 12. Corrections to the first draft

| First draft claimed | Reality |
|---|---|
| Framework, APIs, auth, streaming "unconfirmed" | All four now observed; the extension lacked network access |
| Data model with `QUESTION_STEP` / `FOLLOW_UP` | Flat hash-addressed entities: `query_hash`, canvas UUID, startup attempt |
| Streaming unknown; possibly SSE | No streaming at all. Polling job system |
| "No backend request observable" | 223 requests, 11 endpoints, 176 POST |
| Radix "likely present", medium | Confirmed as the only stack signal from UI; still no framework |
| Single query, 10 → 9 | Two queries, 10 → 9 → 8 |
| 7 sources in the finished view | Varies per run: 7, then 5 of 17 found |

The UI findings held up: six modes, the `style` query parameter, Systematic Review and Max
gated, IEEE citation style, and the transient empty source panel. What the extension could not
reach was everything underneath.

---

## 13. Method and safety

- HAR read programmatically. **No header values were read, printed or stored**; only header
  *names*, and only to establish the negative result that no `Authorization` header exists.
- **No query text, answer text, source titles or abstracts were copied into this document.** The
  request and response bodies contain the user's own questions and generated answers; the
  analysis used field names and type shapes only.
- No credential, cookie or token value appears in this file, and none was extracted.
- Nothing was deleted, purchased, downgraded, or changed in the account. Two queries were
  submitted, consuming two of the ten free queries.
- `scripts/har_surface.py` in the CiteGraph-NLP repository performs this extraction and is
  written so it cannot print a header value even if asked.

## 14. Second capture: page load and bundle analysis

`app.answerthis.io-02.har` — 96 entries, 19.9 MB, one page load. It closed the framework
question and added the vendor, toolchain and auth-storage findings.

- Only **two further header names** across 96 requests, both `x-at-browser-id`. No
  `Authorization`, no `Cookie`, no API-key header. This reproduces the first capture's
  negative result on an independent capture.
- The main bundle arrived base64-encoded in the HAR. Decoded to **11,443,925 characters**.
  A raw `in` test against the encoded text would have found nothing, which is the same trap as
  byte-searching the PDF earlier: the encoding is the obstacle, not the content.
- Fingerprinting used **negative evidence** as the primary signal. `createApp`,
  `defineComponent`, `createSignal` and `platformBrowserDynamic` all return zero, which is what
  excludes Vue, Svelte, Solid and Angular. Positive markers alone would only have shown React
  is *present*, not that it is the only framework.
- A first probe reported 6,463 "vue-ish call sites" from a regex matching bare `h(` and
  `ref(`. That was entirely a false positive inside minified React code, and it would have
  produced a confidently wrong framework identification. Corrected before writing.
- The bundle contains no secrets: no API key, no bearer token, no signing material. Model ID
  strings, host maps and library names only.
- Decoded bundle written to a temp path for analysis and not committed anywhere.

## 15. Third pass: re-examining the captures, and a correction

The user pointed out that *Preserve log* had been enabled all along, contradicting a claim in
the previous revision that the captures missed the polling lifecycle for that reason. **The user
was right and the claim was wrong.** It was asserted as a finding without ever being checked
against the capture.

Re-reading HAR 1 in full:

- **14 `startup/attach` polls across 540 seconds**, timestamps present on all 14, at roughly
  500 ms intervals — the client honouring `retry_after_ms` exactly.
- **State sequence observed in full:** `awaiting_materials` (1) → `provisioning` (12) → a
  terminal poll returning **200** instead of 202. The status code, not a state string, is the
  terminator.
- **A `status: "starting"` field rides alongside `startup_state`** on every 202. Two parallel
  status fields for one lifecycle.
- **The `sources` question is answered.** Of three `answerQ` calls, one had `sources.result`
  empty and two populated. Sources do arrive on a later poll, as the earlier revision only
  suspected.
- **A real credential exists.** The terminal poll's body carries a `backend_jwt` field. This
  means AnswerThis proxies to its own backend, which holds a vendor token the browser never
  sees. Architecturally significant, and consistent with `api.answerthis.io` being the only
  first-party host the client talks to.

Net effect: **four more questions closed, from data that was already supplied.** Nine open became
six. Both captures are good; the remaining items need *deliberate* actions (break a query, toggle
a flag, view the cookie column), not better capture settings.

### Incident: a credential was printed to the terminal

The timeline probe above printed the leading characters of the `backend_jwt` value from the
terminal poll's response body.

- It reached **terminal output only**. No value was written to a file, to either deliverable, or
  to the repository. `git grep` for JWT-shaped strings across all tracked files returns nothing.
- The probe deleted itself and the temp bundle afterwards.
- Cause: the script truncated and printed a response body in order to show its shape, without
  first checking the body for credential fields. This is the precise failure mode the extraction
  tooling was written to avoid, and it happened inside a throwaway probe rather than inside
  `har_surface.py`, which does not read body values.
- A credential printed once in a local terminal is not, by itself, a compromise: it would need to
  be captured from the scrollback, and it is short-lived. It is recorded here so the exposure is
  on the record rather than in a transcript nobody re-reads.
- The lesson generalises, and it is the same one from the PDF byte-search and the "vue-ish call
  sites" probe: **a check that prints data must decide what not to print before it runs, not
  after.**
