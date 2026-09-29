# AnswerThis Study Log

## Scope and safety
- Source task: `answerthis-study-prompt.md` supplied by the user.
- Scope: inspect only the selected, already-open AnswerThis account and user-triggered product flows; do not inspect or record other account content.
- Credentials, auth header values, cookies, tokens, and secret values are never recorded.
- No deletion, billing changes, or upgrades are in scope.
- Started: 2026-09-29.

## Phase 0 — Orient
- Selected URL: `https://app.answerthis.io/ask-answerthis?tab=home`
- Page title: `Best AI research assistant | AnswerThis`
- App behaves as a client-rendered SPA at the observed surface: the app shell loads at a stable URL and in-product UI is interactive without a full document navigation (more route checks pending).
- Evidence available: accessibility tree includes app shell, controls, and transient onboarding tour; initial modal was dismissed via “Skip tour”.
- Framework detection: UNCONFIRMED. The available browser-control surface exposes accessibility state but no read-only DOM evaluation or script-tag inspection.
- Network inspection: UNAVAILABLE through available tools so far. Ctrl+Shift+I from the page did not expose DevTools; no dedicated DevTools/network tool is available. No requests or headers have been collected. Continue with visible UI evidence and record this limitation.
- No unrelated user content was summarized or copied.

## Phase 1 — Stack and surface
- Visible product structure: signed-in app shell with home composer, mode/tool menus, project selector, account/usage controls, saved Searches/Documents filters, canvas detail view, source pane, and Library/AI Writer entry points.
- SPA-style behavior: URL changed among composer mode states and the canvas while the app title and shell remained; this supports SPA-style routing but is not framework proof.
- UI primitive evidence: accessibility menu/popover IDs use `radix-:...:`. Radix-style components are likely; framework and package version remain UNCONFIRMED.
- Frontend framework/version, build tool, bundles, CSS method, state manager, analytics/session replay/error/feature-flag SDKs: UNCONFIRMED because script, DOM, and network inspection were unavailable.
- Visible third-party source links appear in generated results; no auth, payment, support vendor, or analytics embed was identified.

## Phase 2 — Workflows
- Quick Q/A: submitted one neutral factual question. The app opened a canvas route, showed progress milestones, then rendered an answer with inline citations. The query allowance changed from 10 to 9. No other query was submitted.
- Result detail: canvas includes question/title, answer blocks, citation manager (IEEE selected), source pane, follow-up composer, answer feedback/copy, export, Share, and Edit with AI Writer. The source panel went from an early empty/loading state to sources; no article text was copied into this log.
- Mode switching: Quick Q/A was the starting mode. Literature Review changed the `style` parameter to `full-review`; Presentation, Data Analysis, and Research Gaps changed it to corresponding mode values and changed the prompt placeholder. Selecting Systematic Review navigated to `/slr/new` and showed Pro/Research/Max gating; returned without checkout.
- Model effort: Normal is the current default (“Fast answers”); Max (“Maximum depth”) is labeled Upgrade. Max was not selected.
- Tools menu: Find Papers opened a paper-topic composer. Paper Chat returned to the generic Q/A composer. Paraphraser opened tone choices (Academic, Fluent, Formal, Creative, Simple), LEN/VAR sliders, text input, and a disabled Rephrase control until text is entered. Trial Landscape opened an indication/intervention composer. No paid gate appeared for the sampled screens; no tool output was requested.
- Saved items: Searches listed the one study-created search under the default project, with a step count. Documents showed “No documents yet” and a Go to Library control. Opening the saved search reopened the same canvas detail.
- Network capture: none. Methods, paths, statuses, payload fields, backend services, and request counts are UNOBSERVED; this must not be interpreted as zero requests.

## Phase 3 — Streaming
- The on-screen timer reached about 1m20s when answer text first appeared; the completed answer view appeared about 1m30s after submission. Timing is approximate.
- Visible stages included submission, analysis/workspace setup, source retrieval, drafting, and delivery; 12 sources were reported found during work and the completed view showed 7.
- Transport, event/message envelope, termination marker, separate question/answer calls, and failure payload: UNCONFIRMED because the Network panel was unavailable.
- A Stop button was visible while the query ran; cancellation was not tested. No failure was deliberately triggered.

## Phase 4 — Bundles
- No script tags, loaded bundle names, content hashes, API base URL, environment constants, route table strings, endpoint strings, or feature-flag keys could be inspected using the available browser surface.
- No assets were copied or downloaded. Bundle and auth architecture remain UNCONFIRMED.

## Phase 5 — Write-up
- Saved the architecture report as `answerthis-architecture.md` in the requested study folder under the workspace `outputs/` directory.
- This log records observations only and omits source titles/abstracts, generated answer text, and credential values.
- Completed: 2026-09-29.

## Network-recording replay — 2026-09-29
- The user restarted the selected AnswerThis page after browser control failed on the first replay attempt. Control then worked in the restarted tab.
- Revisited the free research/tool modes, including Literature Review, Data Analysis, Research Gaps, Presentation, Find Papers, Paper Chat, Paraphraser, Trial Landscape, and Quick Q/A. The paid Systematic Review and Max modes were not activated.
- Opened Searches, Documents, and All; reopened the study-created saved search; visited its Sources, Answers, and Methodology views.
- Submitted one new neutral Quick Q/A question about ocean tides. The allowance changed from 9 to 8.
- Generation completed after roughly 2 minutes 45 seconds. The UI reported 10 sources after the first search pass, 17 after a second pass, and 5 in the finished answer view.
- The user recorded network traffic independently. No network log, request headers, credentials, or tokens were accessed or saved by this study.

## HAR analysis — 2026-09-29 (correction pass)

The user supplied a HAR capture after this study reported that network inspection was
unavailable. Its limitation was a tooling one, not a method one: the browser-control surface
exposes the accessibility tree and screenshots but not the Network panel, so Phases 1, 3 and 4
could not be completed as written.

- Input: `app.answerthis.io.har`, 223 entries, 5.2 MB, WebInspector 537.36.
- Processed with `scripts/har_surface.py` in the CiteGraph-NLP repository, which reads field
  names and type shapes only. No header value, cookie, or token was read, printed or stored.
  The tool cannot print a header value by construction.
- 176 POST, 43 GET, 4 OPTIONS. One first-party API host plus PostHog (115), Sentry (30),
  Intercom (5) and one telemetry beacon (2).
- Eleven first-party endpoints recovered, including a per-session **E2B sandbox** at a random
  subdomain, which no amount of UI inspection would have revealed.
- The generation flow is a **polling job system**, not a streaming response: a 202 with
  `startup_state` and `retry_after_ms: 500`, polled 14 times in one run, then one 22 KB
  `answerQ` response carrying the whole answer plus a `content_sha256`. The UI's apparent
  streaming is client-side rendering of that state machine.
- **No `Authorization` or `Cookie` header on any request.** `x-at-browser-id` appears on 31.
  The session mechanism itself remains unconfirmed; cookie attachment is the likely explanation
  but was not proven.
- The `filters` object in the `answerQ` response exposes a configuration surface far richer
  than the UI shows, most notably a `documentStructure` group controlling section count,
  subheadings per section, custom sections and a `strictness` level. Template-driven
  generation, not a single prompt.
- `GET /api/usage_limits` shows `limit: 0` for the paid categories, so the paywall is enforced
  in the API response rather than only hidden in the interface.

Corrections written back into `answerthis-architecture.md`: the inferred data model (which had
invented `QUESTION_STEP` and `FOLLOW_UP` entities), the streaming answer, the "no backend
request observable" conclusion, the source counts, and the query count. The UI-only findings
were re-checked and all held: six modes, the `style` parameter, Systematic Review and Max
gated, IEEE citations, and the transient empty source panel — which the HAR context now
explains, since `sources.result` was empty in the captured responses and evidently populates
on a later poll that was not captured.

Still unconfirmed after this pass: the frontend framework and build tool, because the capture
begins after page load and contains no script tags; the session auth mechanism; the full set
of `startup_state` values; and the `failure_receipt` shape. A HAR captured across a page
reload would settle the first of those immediately.

Safety unchanged: nothing deleted, purchased or downgraded; two queries submitted against the
user's own free-tier account; no credential, query text, answer text or source content
recorded in either file.

## Second HAR and bundle analysis — 2026-09-29 (open question closed)

The user supplied a second capture taken across a page load, which is what Phase 4 originally
needed. 96 entries, 19.9 MB, one page.

- **Framework closed: React + Vite.** `createElement` x1477, JSX runtime x15845, `useState`
  x1627, `createRoot` x3, `__vite` x83. Zero `createApp`, `defineComponent`, `createSignal` or
  `platformBrowserDynamic`; zero webpack, esbuild or rollup markers. State is Zustand with
  `persist` middleware, confirmed by a `[zustand persist middleware]` string in the bundle.
- The bundle is split into `index` (11.4 MB decoded), `vendor` (130 KB) and `utils` (90 KB),
  with content hashes in the filenames (`index.DsxRCgNZ.js`).
- **It arrived base64-encoded in the HAR.** A naive substring test against the stored text
  finds nothing, because the bytes are not JS. Decoded first, then analysed. Same class of
  error as byte-searching a compressed PDF earlier in the work, and worth writing down.
- **A first fingerprint probe was wrong and was caught.** It reported 6,463 "vue-ish call
  sites" from a regex matching bare `h(` and `ref(` inside minified React. That would have
  produced a confident and entirely false framework identification. Replaced with a probe
  testing for constructs that cannot occur in a React bundle, which also produced the negative
  evidence that actually excludes the alternatives.
- **Auth negative result reproduced.** Two further header names across 96 requests, both
  `x-at-browser-id`. No `Authorization`, no `Cookie`. Combined with 109 `localStorage` and 63
  `sessionStorage` references in the bundle, a browser-storage session is likely, but a HAR
  omitting a cookie is weak evidence and this is recorded as inferred, not observed.
- **Vendor identified: Anthropic.** The bundle names `claude-opus-4-5-20251101`,
  `claude-sonnet-4-5-20250929` and `claude-haiku-4-5-20251001`. The mapping onto the Normal and
  Max effort control is inferred from tier shape, not observed in a request.
- **A second backend exists.** A host map in the bundle pairs `app.answerthis.io` with
  `api.answerthis.io` and `new-api.answerthis.io`, a staged-rollout pattern.
- **Citations are done properly:** an embedded CSL/citeproc implementation with styles fetched
  from `apastyle.apa.org`, plus IEEE support and DOI resolution. Citation style is data, not
  code.
- **Instrumentation sprawl:** RudderStack and PostHog both fire, alongside Google Tag Manager,
  a Facebook pixel and a TikTok pixel, plus Sentry, Intercom and a `prodregistryv2.org` beacon.
  Five analytics systems on one app, alongside an 11.4 MB bundle.
- No secret was present in the bundle: no API key, bearer token or signing material. Model ID
  strings, host maps and library names only.
- The decoded bundle was written to a temp path for analysis and committed nowhere.

Open questions reduced from nine to seven. The cheapest remaining one is a DevTools screenshot
of the request headers with the cookie column visible, which would settle the auth mechanism in
a single glance.

## Third pass — correction to the second — 2026-09-29

The user reported that *Preserve log* had been enabled, contradicting the previous log entry's
claim that the captures missed the polling lifecycle for that reason. **The user was right.**

- HAR 1 contains **14 `startup/attach` polls across 540 seconds**, all timestamped, at ~500 ms
  intervals. Preserve log worked. The earlier claim was asserted without checking the capture.
- **Full state sequence observed:** `awaiting_materials` → `provisioning` ×12 → a terminal poll
  returning **200** rather than 202. The HTTP status code is the completion signal, not a state
  string — a cleaner design than the earlier revision credited it with understanding.
- Every 202 also carries a `status: "starting"` field beside `startup_state`.
- **`sources` question closed:** of three `answerQ` calls, one had `sources.result` empty and two
  populated. Confirmed from the capture rather than suspected.
- **A `backend_jwt` field is present** in the terminal poll's response body. A real credential
  exists, held server-side behind AnswerThis's own API. Existence closed; transport still open.
- No application error appears in either capture: the only ≥400 first-party responses are 404s on
  `favicon.ico`. `failure_receipt` is therefore not recoverable from existing data.

Open questions: nine → **six**. Both captures are sound; the remainder need deliberate actions —
break a query, toggle a sandbox flag, open the cookie column — not different capture settings.

### Incident: credential printed to terminal

The probe that produced the poll timeline truncated and printed response bodies, and the terminal
poll's body contains a `backend_jwt`. Leading characters of that token appeared in terminal
output.

- Terminal output only. Nothing written to a file, to either deliverable, or to the repository.
  `git grep` for JWT-shaped strings across tracked files: none.
- The probe and the decoded bundle were deleted immediately after.
- Cause: the probe printed a body to show its shape without first checking it for credential
  fields. `har_surface.py`, the committed tool, does not read body values; this was throwaway
  code written without that discipline.
- Not a compromise by itself — it would need to be captured from scrollback, and it is
  short-lived — but recorded so the exposure is documented rather than buried in a transcript.
- Generalisable lesson, and the third instance today: a check that prints data must decide what
  not to print **before** it runs. The others were byte-searching a compressed PDF and a regex
  reporting 6,463 false Vue call sites.
