# Competitive reference: AnswerThis

A reverse-engineering study of **answerthis.io**, carried out on 2026-09-29 against an
account the study's author owns. Two HAR exports were captured, plus one decoded JavaScript
bundle. This directory holds the resulting write-up.

## Files

| File | What it is |
|---|---|
| `answerthis-architecture.md` | The findings. Every claim tagged *observed*, *observed-UI* or *inferred*. |
| `answerthis-study-log.md` | The chronological log, including two corrections and one incident. |

## Provenance and standing

**How it was captured.** Two DevTools HAR exports against a user-owned throwaway account,
plus the application's own already-loaded JS bundle. The browser-control tooling available at
the time could read the accessibility tree and take screenshots but could not see network
traffic, so the first pass was written from UI observation alone and the architecture it
described was substantially wrong. The HAR exports replaced it.

**What this is not.** This is a client-and-traffic-level study of one product on one day. It
says nothing about AnswerThis's retrieval stack, its prompt design, or its evaluation, none
of which are observable from outside. Six questions remain open. Do not read this as a
benchmark or as a performance comparison — it is a structural note.

**No credentials are recorded.** No API key, token, cookie or auth header value appears in
either file. Request and response bodies were read for field *names* and type *shapes* only;
query text, generated answers and source content were deliberately excluded.

## Two corrections kept visible

Both are recorded in the documents rather than quietly fixed, because a study that hides its
own mistakes cannot be trusted on the parts it got right.

1. **A false framework fingerprint.** A first probe reported 6,463 "Vue call sites" from a
   regex matching bare `h(` and `ref(` inside minified React. The actual framework is React +
   Vite, established by 15,845 JSX-runtime hits *and* the absence of every competing marker.
   The negative evidence is what excludes Vue, Svelte, Solid and Angular.
2. **A wrong claim about capture settings.** A revision stated the captures missed the polling
   lifecycle because *Preserve log* was off. It was on, and worked. The state sequence
   `awaiting_materials` → `provisioning` ×12 → terminal `200` had been in the file the whole
   time. The claim was asserted without being checked.

## One incident, on the record

A throwaway timeline probe truncated and printed response bodies, and one poll's body contains
a `backend_jwt`. Leading characters reached terminal output only — nothing was written to a
file, to either document, or to the repository. The probe and the decoded bundle were deleted.

The generalisable lesson is recorded in the study: **a check that prints data must decide what
not to print before it runs.** The same failure shape appeared twice more in that project — a
byte-search of a compressed PDF that found neither of two strings, and the false Vue count
above.

## What it changed in CiteGraph

The study is recorded here because three things were taken from it, and because two things
deliberately were not.

**Taken.** A server-driven poll interval (`retry_after_ms`) rather than a hardcoded one; CSL
style files for citation export, so a style is data and adding one is a file drop; and
server-side credential handling, since CiteGraph now calls two external providers.

**Not taken, because CiteGraph is already better on it.** AnswerThis terminates a job on the
HTTP status code. CiteGraph derives status from a typed body with a safe default, so a
malformed response cannot hang the poll. That difference is now a documented design decision
in Chapter 4, with the argument for it, because a reviewer who knows the alternative will ask.

**Not taken: the instrumentation.** AnswerThis runs five analytics systems — PostHog,
RudderStack, Google Tag Manager, a Facebook pixel and a TikTok pixel — on an 11.4 MB bundle.
Recorded as an anti-pattern. CiteGraph ships none of them.

## Open questions

Six remain. None would change a line of CiteGraph, and none are worth further capture effort
for this project's purposes. They are listed in `answerthis-architecture.md` §11 with what
would settle each.
