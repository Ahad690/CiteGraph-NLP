import type { RunPayload, RunResult, RunStatus, RunStatusPayload } from "@/types/api";

/** Treat any payload that has the `papers` array AND `seed_paper_id` as a
 *  completed RunResult. Status fields without `papers` are RunStatusPayload.
 *  This is stricter than checking just for `papers`, so a malformed partial
 *  response cannot accidentally be classified as completed. */
export function isCompletedRunResult(payload: RunPayload): payload is RunResult {
  return (
    "papers" in payload &&
    Array.isArray((payload as RunResult).papers) &&
    typeof (payload as RunResult).seed_paper_id === "string" &&
    Array.isArray((payload as RunResult).citation_edges)
  );
}

export function isRunStatusPayload(payload: RunPayload): payload is RunStatusPayload {
  return !isCompletedRunResult(payload);
}

/** Derive a status string regardless of which payload shape came back.
 *  A RunResult-shape response implies status="completed" even if the
 *  field is absent from the wire payload. */
export function deriveStatus(payload: RunPayload): RunStatus {
  if (isCompletedRunResult(payload)) {
    return (payload as RunResult).status ?? "completed";
  }
  return (payload as RunStatusPayload).status ?? "started";
}

/** Fill missing arrays/strings with safe defaults so dashboard pages can
 *  destructure RunResult without per-component optional guards. This is the
 *  single source of truth for the dashboard's run shape. */
export function normalizeRun(payload: RunPayload): RunResult {
  const completed = isCompletedRunResult(payload);
  const base = payload as Partial<RunResult> & RunStatusPayload;
  return {
    run_id: base.run_id,
    status: deriveStatus(payload),
    seed_paper_id: base.seed_paper_id ?? "",
    papers: completed ? (payload as RunResult).papers : [],
    population_resolutions: completed ? (payload as RunResult).population_resolutions ?? [] : [],
    population_candidates: completed ? (payload as RunResult).population_candidates ?? [] : [],
    citation_edges: completed ? (payload as RunResult).citation_edges ?? [] : [],
    ranked_foundational_papers: completed
      ? (payload as RunResult).ranked_foundational_papers ?? []
      : [],
    ranked_paths: completed ? (payload as RunResult).ranked_paths ?? [] : [],
    warnings: completed ? (payload as RunResult).warnings ?? [] : [],
    created_at: base.created_at ?? new Date().toISOString(),
  };
}

/** Backend error strings can contain stack traces, file paths, or provider
 *  URLs. Convert known patterns into user-safe messages; unknown errors
 *  collapse to a generic message + diagnostic ID so the support flow is
 *  unblocked without leaking internals. */
export function userFacingError(error: string | null | undefined, runId: string): {
  message: string;
  diagnosticId: string;
} {
  const safe = (() => {
    if (!error) {
      return "The analysis could not complete.";
    }
    const s = String(error);
    // Known, safe-to-show categories
    if (/no papers found to merge/i.test(s)) {
      return "We couldn't resolve this paper through any of our metadata providers (OpenAlex, Crossref, Europe PMC). Try a different DOI or PMID.";
    }
    if (/timeout|timed out/i.test(s)) {
      return "The analysis timed out while contacting external metadata providers. Try again later.";
    }
    if (/aborted due to server shutdown/i.test(s)) {
      return "The analysis was interrupted by a server restart. Please retry.";
    }
    if (/rate limit/i.test(s)) {
      return "A metadata provider rate-limited the request. Try again in a few minutes.";
    }
    // Anything else: generic message — do not show the raw string.
    return "The analysis pipeline could not complete. Try a different seed paper.";
  })();

  return { message: safe, diagnosticId: runId };
}
