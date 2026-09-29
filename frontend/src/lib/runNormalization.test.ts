/**
 * The poll contract.
 *
 * CiteGraph derives run status from the response BODY, and derives it from a
 * default when the body is unusable. That is the property worth defending:
 * answerthis, the system this was compared against, terminates a job on the
 * HTTP status code instead, so a lost or mangled response there reads as a
 * finished job. Here it cannot, and these tests are why that claim is more than
 * an assertion in a comment.
 *
 * The two ways a poll can go wrong are both silent: it never stops, and it stops
 * early. Neither shows up as an error, and both look like a working feature.
 */
import { describe, expect, it } from "vitest";
import { deriveStatus, isCompletedRunResult, normalizeRun } from "./runNormalization";
import type { RunPayload, RunStatusPayload } from "@/types/api";

const status = (s: string, extra: Partial<RunStatusPayload> = {}): RunPayload =>
  ({ run_id: "r1", status: s, created_at: "2026-01-01T00:00:00Z", ...extra }) as RunPayload;

const result = (over: Record<string, unknown> = {}): RunPayload =>
  ({
    run_id: "r1",
    seed_paper_id: "p1",
    papers: [{ paper_id: "p1", title: "T", authors: [] }],
    citation_edges: [],
    ...over,
  }) as unknown as RunPayload;

describe("completed detection", () => {
  it("recognises a full result", () => {
    expect(isCompletedRunResult(result())).toBe(true);
  });

  it("does not treat a status payload as a result", () => {
    expect(isCompletedRunResult(status("completed"))).toBe(false);
  });

  it("does not treat an empty papers array as incomplete", () => {
    // A run can legitimately complete having found nothing. Stopping the poll on
    // an empty result is a real bug: the dashboard would show a finished run
    // before the orchestrator has finished writing.
    expect(isCompletedRunResult(result({ papers: [] }))).toBe(true);
  });

  it("rejects a partial body that happens to have papers", () => {
    // The dangerous shape: papers present, seed_paper_id missing. A naive
    // `if (payload.papers)` check would call this completed.
    const partial = { run_id: "r1", papers: [], citation_edges: [] } as unknown as RunPayload;
    expect(isCompletedRunResult(partial)).toBe(false);
  });

  it("rejects a body whose papers field is not an array", () => {
    const partial = {
      run_id: "r1",
      seed_paper_id: "p1",
      papers: "not an array",
      citation_edges: [],
    } as unknown as RunPayload;
    expect(isCompletedRunResult(partial)).toBe(false);
  });
});

describe("deriveStatus", () => {
  it("defaults to started when a result carries no status", () => {
    // The safety property. A result with no status field still implies the run
    // finished, and stopping is correct.
    expect(deriveStatus(result())).toBe("completed");
  });

  it("defaults to started for an unusable body", () => {
    // The other safety property, and the reason this beats a status-code
    // terminator: garbage keeps the poll ALIVE rather than ending it.
    const garbage = { nonsense: true } as unknown as RunPayload;
    expect(deriveStatus(garbage)).toBe("started");
  });

  it("passes a real status through", () => {
    expect(deriveStatus(status("running"))).toBe("running");
  });

  it("reports failed rather than hiding it", () => {
    expect(deriveStatus(status("failed"))).toBe("failed");
  });

  it("accepts the legacy pending and processing values", () => {
    // The backend never emits these -- grep found no match in src -- but they
    // were in the client's poll set and may exist in stored runs from before a
    // rename. Tolerating them is deliberate; the test documents the decision.
    expect(deriveStatus(status("pending"))).toBe("pending");
    expect(deriveStatus(status("processing"))).toBe("processing");
  });
});

describe("normalizeRun", () => {
  it("fills defaults so a page can destructure without guards", () => {
    const n = normalizeRun(status("running") as RunStatusPayload);
    expect(Array.isArray(n.papers)).toBe(true);
    expect(Array.isArray(n.citation_edges)).toBe(true);
    expect(n.run_id).toBe("r1");
  });
});
