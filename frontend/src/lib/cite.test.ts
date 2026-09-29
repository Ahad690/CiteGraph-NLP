/**
 * Tests for the citation exporter.
 *
 * The risk guarded here is specific: an exporter that throws, or emits an empty
 * file, looks identical to one that works until a user opens their reference
 * manager. So these assert on the produced text, not that a function was called.
 *
 * The CSL engine needs a vendored style and locale, which arrive by fetch, so
 * `fetch` is stubbed with the real files. That keeps the tests offline while
 * still proving the shipped style and locale actually parse -- a style file that
 * does not load would otherwise surface only in a browser.
 *
 * The stub must serve the LOCALE as well as the styles. The first version
 * answered every URL with the APA style, so the locale fetch returned style XML
 * and the processor failed on a missing `language` node. The error named the
 * locale and pointed away from the stub, which is why the wrong locale shape was
 * implemented twice before the cause was found.
 */

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  collectCiteable,
  exportCitations,
  lowConfidenceCount,
  previewCitations,
  splitAuthor,
  LOW_CONFIDENCE_THRESHOLD,
} from "./cite";
import type { RunResult, Paper } from "@/types/api";
import APA_CSL from "../../public/csl/apa.csl?raw";
import IEEE_CSL from "../../public/csl/ieee.csl?raw";
import LOCALE_XML from "../../public/csl/locales-en-US.xml?raw";

function serve(url: string): Response {
  const target = String(url);
  let body: string;
  if (target.includes("locales-en-US")) body = LOCALE_XML;
  else if (target.includes("ieee")) body = IEEE_CSL;
  else body = APA_CSL;
  return { ok: true, status: 200, text: async () => body } as Response;
}

function paper(over: Partial<Paper> = {}): Paper {
  return {
    paper_id: "p1",
    title: "A study of something",
    authors: ["Smith, John"],
    year: 2021,
    journal: "Journal of Testing",
    doi: "10.1234/abc",
    ...over,
  } as Paper;
}

function run(over: Partial<RunResult> = {}): RunResult {
  return {
    run_id: "run123",
    seed_paper_id: "p1",
    papers: [paper()],
    citation_edges: [],
    ...over,
  } as RunResult;
}

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => serve(url)),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("splitAuthor", () => {
  it("splits a comma form", () => {
    expect(splitAuthor("Smith, John")).toEqual({ family: "Smith", given: "John" });
  });

  it("splits a last-word form", () => {
    expect(splitAuthor("Ada Lovelace")).toEqual({ family: "Lovelace", given: "Ada" });
  });

  it("keeps a single word whole", () => {
    expect(splitAuthor("Aristotle")).toEqual({ family: "Aristotle" });
  });

  it("returns null for an empty name", () => {
    expect(splitAuthor("   ")).toBeNull();
  });
});

describe("collectCiteable", () => {
  it("carries no confidence for the seed paper", () => {
    const [entry] = collectCiteable(run());
    expect(entry.confidence).toBeNull();
  });

  it("takes the highest-confidence incoming link per paper", () => {
    const r = run({
      papers: [paper({ paper_id: "seed" }), paper({ paper_id: "p2" }), paper({ paper_id: "p3" })],
      citation_edges: [
        { source_paper_id: "p2", target_paper_id: "seed", confidence: 0.4 },
        { source_paper_id: "p3", target_paper_id: "seed", confidence: 0.9 },
      ],
    } as Partial<RunResult>);
    const byId = Object.fromEntries(
      collectCiteable(r).map((e) => [e.paper.paper_id, e.confidence]),
    );
    expect(byId.seed).toBeNull();
    expect(byId.p2).toBeCloseTo(0.4);
    expect(byId.p3).toBeCloseTo(0.9);
  });
});

describe("low confidence annotation", () => {
  const edge = (id: string, confidence: number) => ({
    source_paper_id: id,
    target_paper_id: "seed",
    confidence,
  });

  it("counts only links below the threshold", () => {
    const r = run({
      papers: [paper({ paper_id: "seed" }), paper({ paper_id: "lo" }), paper({ paper_id: "hi" })],
      citation_edges: [edge("lo", 0.2), edge("hi", 0.95)],
    } as Partial<RunResult>);
    expect(lowConfidenceCount(r)).toBe(1);
  });

  it("puts a note on a low-confidence BibTeX entry", async () => {
    const r = run({
      papers: [
        paper({ paper_id: "seed", title: "The seed paper" }),
        paper({ paper_id: "lo", title: "A shaky paper", doi: "10.1234/lo" }),
      ],
      citation_edges: [edge("lo", 0.2)],
    } as Partial<RunResult>);
    const { body } = await exportCitations(r, "apa", "bibtex");
    expect(body).toContain("note =");
    expect(body).toContain("low confidence");
  });

  it("puts no note on a high-confidence entry", async () => {
    const r = run({
      papers: [
        paper({ paper_id: "seed", title: "The seed paper" }),
        paper({ paper_id: "hi", title: "A solid paper", doi: "10.1234/hi" }),
      ],
      citation_edges: [edge("hi", 0.99)],
    } as Partial<RunResult>);
    const { body } = await exportCitations(r, "apa", "bibtex");
    expect(body).not.toContain("low confidence");
  });

  it("annotates the preview for a low-confidence entry", async () => {
    // Neither vendored style renders a CSL `note` variable, so the note is
    // appended by us. This test exists because a `note` on the CSL item is
    // accepted by the processor and then silently dropped from the output.
    const r = run({
      papers: [
        paper({ paper_id: "seed", title: "The seed paper" }),
        paper({ paper_id: "lo", title: "A shaky paper", doi: "10.1234/lo" }),
      ],
      citation_edges: [edge("lo", 0.2)],
    } as Partial<RunResult>);
    const lines = await previewCitations(r, "apa");
    expect(lines.some((l) => l.includes("low confidence"))).toBe(true);
  });

  it("puts a note on a low-confidence RIS record", async () => {
    const r = run({
      papers: [
        paper({ paper_id: "seed", title: "The seed paper" }),
        paper({ paper_id: "lo", title: "A shaky paper", doi: "10.1234/lo" }),
      ],
      citation_edges: [edge("lo", 0.1)],
    } as Partial<RunResult>);
    const { body } = await exportCitations(r, "apa", "ris");
    expect(body).toContain("N1  -");
    expect(body).toContain("low confidence");
  });
});

describe("exportCitations", () => {
  it("returns an empty body for a run with no papers", async () => {
    const { body } = await exportCitations(run({ papers: [] }), "apa", "bibtex");
    expect(body).toBe("");
  });

  it("produces a BibTeX entry with title, author, year and DOI", async () => {
    const { body, filename, mime } = await exportCitations(run(), "ieee", "bibtex");
    expect(filename).toBe("citegraph-run123-ieee.bib");
    expect(mime).toContain("bibtex");
    expect(body).toMatch(/@article\{/);
    expect(body).toContain("A study of something");
    expect(body).toContain("Smith, John");
    expect(body).toContain("year = {2021}");
    expect(body).toContain("10.1234/abc");
  });

  it("joins BibTeX authors with 'and'", async () => {
    const { body } = await exportCitations(
      run({ papers: [paper({ authors: ["Ada Lovelace", "Turing, Alan"] })] }),
      "apa",
      "bibtex",
    );
    expect(body).toContain("Lovelace, Ada and Turing, Alan");
  });

  it("produces a RIS file with the standard tags", async () => {
    const { body, filename } = await exportCitations(run(), "apa", "ris");
    expect(filename).toBe("citegraph-run123-apa.ris");
    expect(body).toContain("TY  - JOUR");
    expect(body).toContain("TI  - A study of something");
    expect(body).toContain("PY  - 2021");
    expect(body).toContain("DO  - 10.1234/abc");
    expect(body).toContain("ER  -");
  });

  it("emits a complete RIS record for every paper", async () => {
    const r = run({
      papers: [paper({ paper_id: "p1" }), paper({ paper_id: "p2", doi: "10.1234/def" })],
    } as Partial<RunResult>);
    const { body } = await exportCitations(r, "apa", "ris");
    expect(body.split("ER  -").length - 1).toBe(2);
  });

  it("omits a year that is absent rather than inventing one", async () => {
    const { body } = await exportCitations(
      run({ papers: [paper({ year: undefined })] }),
      "apa",
      "ris",
    );
    expect(body).not.toContain("PY  -");
  });

  it("emits one BibTeX entry per paper", async () => {
    // The two papers must differ in content as well as in id: citeproc renders
    // one line for two items whose title and DOI are identical, listing both ids
    // on it. A test that passed the same paper twice would assert 2 and get 1,
    // and the cause would look like a dedup bug in our own code.
    const r = run({
      papers: [
        paper({ paper_id: "p1", title: "First paper", doi: "10.1234/one" }),
        paper({ paper_id: "p2", title: "Second paper", doi: "10.1234/two" }),
      ],
    } as Partial<RunResult>);
    const { body } = await exportCitations(r, "apa", "bibtex");
    expect(body.split("@article{").length - 1).toBe(2);
  });

  it("renders differently under APA and IEEE", async () => {
    const apa = await previewCitations(run(), "apa");
    const ieee = await previewCitations(run(), "ieee");
    expect(apa.join("")).not.toBe(ieee.join(""));
  });

  it("produces non-empty styled citations", async () => {
    const apa = await previewCitations(run(), "apa");
    expect(apa.length).toBe(1);
    expect(apa[0].length).toBeGreaterThan(20);
    expect(apa[0]).toContain("A study of something");
  });

  it("reports a style that cannot be loaded", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 404, text: async () => "" }) as Response),
    );
    await expect(exportCitations(run(), "apa", "bibtex")).rejects.toThrow(/could not be loaded/);
  });
});
