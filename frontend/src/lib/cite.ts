/**
 * Citation export: CiteGraph records to BibTeX or RIS, styled with CSL.
 *
 * WHY CSL RATHER THAN FORMATTING BY HAND. Citation style is data. A CSL style is
 * a JSON file, so supporting APA, IEEE and Chicago is a file drop rather than
 * three hand-written formatters that each get the punctuation rules subtly
 * wrong. This is the single most transferable idea from the answerthis study,
 * whose bundle embeds a full citeproc implementation.
 *
 * WHY THE STYLES ARE VENDORED. citeproc normally fetches styles over the
 * network. An export is a thing a user does on a possibly bad connection and
 * expects to work, and a citation file that fails because a CDN is unreachable
 * is a citation file nobody gets. Both styles and the locale live in /public/csl.
 *
 * WHY CONFIDENCE APPEARS IN THE OUTPUT, AND WHY IT IS APPENDED RATHER THAN
 * STYLED. Every edge CiteGraph produces carries a link-confidence score, and
 * that is the product's central claim. A provenance field that only exists in
 * the data is invisible the moment it is exported, which is exactly where a user
 * stops being able to check anything.
 *
 * It is appended to the styled string rather than passed as a CSL `note`
 * because NEITHER APA NOR IEEE RENDERS THAT VARIABLE. Both vendored styles
 * contain no `variable="note"` anywhere, so a note placed on the item is
 * accepted by the processor and silently dropped from the output. That was
 * found by a test asserting the marker appears in the rendered text, which
 * passed for the plain citation and failed for the noted one. Appending keeps the
 * feature independent of what a given style happens to support.
 *
 * The note is confined to entries below the threshold. Restating a high
 * confidence on every entry would be noise that trains a reader to ignore the
 * field, which defeats the purpose.
 */

import type { RunResult, Paper, CitationEdge } from "@/types/api";

/** A link below this confidence is annotated in the export. */
export const LOW_CONFIDENCE_THRESHOLD = 0.5;

export type CitationStyle = "apa" | "ieee";
export type CitationFormat = "bibtex" | "ris";

const STYLE_URLS: Record<CitationStyle, string> = {
  apa: "/csl/apa.csl",
  ieee: "/csl/ieee.csl",
};

/** The vendored CSL locale, needed by the processor and not by the styles. */
const LOCALE_URL = "/csl/locales-en-US.xml";

const LOCALE = "en-US";

/** A paper plus the link-confidence that connects it to the seed, if any. */
export interface CiteablePaper {
  paper: Paper;
  /** Null for the seed paper, which is not linked to itself. */
  confidence: number | null;
}

type CslItem = Record<string, unknown>;

/** citeproc wants CSL locale XML, not a locale code and not JSON. */
let localePromise: Promise<string> | null = null;

function loadLocale(): Promise<string> {
  if (!localePromise) {
    localePromise = fetch(LOCALE_URL).then((res) => {
      if (!res.ok) throw new Error(`CSL locale could not be loaded (${res.status})`);
      return res.text();
    });
  }
  return localePromise;
}

async function loadStyle(style: CitationStyle): Promise<string> {
  const res = await fetch(STYLE_URLS[style]);
  if (!res.ok) {
    throw new Error(`CSL style "${style}" could not be loaded (${res.status})`);
  }
  return res.text();
}

/**
 * Split a provider's author string into CSL family/given parts.
 *
 * Providers are inconsistent: "Smith, John", "John Smith" and "J. Smith" all
 * appear across Crossref, OpenAlex and Europe PMC. CSL renders correctly or not
 * at all depending on which fields are filled, and a name left as one literal
 * string comes out as a bare drop in every style. Splitting on the last space is
 * a heuristic, and a wrong split is a wrong initial rather than a missing name,
 * which is the lesser failure.
 */
export function splitAuthor(raw: string): { family: string; given?: string } | null {
  const name = raw.trim();
  if (!name) return null;
  if (name.includes(",")) {
    const [family, given] = name.split(",", 2);
    const out: { family: string; given?: string } = { family: family.trim() };
    if (given && given.trim()) out.given = given.trim();
    return out;
  }
  const parts = name.split(/\s+/);
  if (parts.length === 1) return { family: parts[0] };
  const family = parts.pop() as string;
  return { family, given: parts.join(" ") };
}

/**
 * Decide a CSL item type.
 *
 * The frontend `Paper` type carries no publication-type vocabulary and the three
 * providers do not agree on one, so this does not guess. `article-journal` is the
 * one type a container name supports, and every CSL style renders it, so an
 * unrecognised record lands in a shape the user can still read.
 */
function cslType(paper: Paper): string {
  const declared = (paper as { publication_type?: string | null }).publication_type;
  return declared || "article-journal";
}

/**
 * Give every paper a distinct CSL id.
 *
 * A DOI was the obvious id, and it is wrong: CiteGraph's whole problem is
 * providers disagreeing about records, so a run can legitimately contain two
 * papers the same DOI resolved to, or the same paper under two identifiers.
 * citeproc's registry is keyed by id, so duplicates collapse -- the second paper
 * vanishes from the export with no error. A test asserting one entry per paper
 * caught this: it returned 1 where 2 papers were passed.
 *
 * The paper_id is the CiteGraph-native key and is unique within a run by
 * construction, so it is used for the CSL id and the DOI stays a field. The
 * generated cite key prefers the DOI because it is the more readable handle, but
 * is disambiguated when two papers share one.
 */
function toCslItem(entry: CiteablePaper, index: number): CslItem {
  const { paper } = entry;
  const id = paper.paper_id || `paper-${index + 1}`;

  const item: CslItem = {
    id,
    type: cslType(paper),
    title: paper.title,
    DOI: paper.doi ?? undefined,
    URL: paper.doi ? `https://doi.org/${paper.doi}` : undefined,
    // CSL wants a date-part object, not a bare year. An absent year stays
    // absent: a fabricated date is worse in a citation than a missing one.
    issued: paper.year ? { "date-parts": [[paper.year]] } : undefined,
    "container-title": paper.journal ?? undefined,
  };

  const authors = (paper.authors ?? [])
    .map(splitAuthor)
    .filter((a): a is { family: string; given?: string } => a !== null);
  if (authors.length) item.author = authors;

  // Drop undefined keys so the processor does not see an explicit null and
  // render an empty field.
  for (const key of Object.keys(item)) {
    if (item[key] === undefined) delete item[key];
  }
  return item;
}

/** Highest-confidence incoming link per paper, which is the link that matters. */
function confidencesByPaper(edges: CitationEdge[]): Map<string, number> {
  const best = new Map<string, number>();
  for (const edge of edges) {
    const c = edge.confidence;
    if (typeof c !== "number") continue;
    const current = best.get(edge.source_paper_id);
    if (current === undefined || c > current) best.set(edge.source_paper_id, c);
  }
  return best;
}

/**
 * Build the citeable set: every paper in the run, each carrying the confidence
 * of the link that put it in this graph. The seed gets null, because it is not
 * linked to anything -- it is where the links start.
 */
export function collectCiteable(run: RunResult): CiteablePaper[] {
  const confidences = confidencesByPaper(run.citation_edges ?? []);
  return (run.papers ?? []).map((paper) => ({
    paper,
    confidence: confidences.get(paper.paper_id) ?? null,
  }));
}

function lowConfidenceNote(confidence: number): string {
  return ` [CiteGraph: linked to the seed paper with low confidence ${confidence.toFixed(2)}; verify before relying on it.]`;
}

/**
 * A rendered citation, carrying the input index of the paper it came from.
 *
 * The index is carried rather than assumed positionally because citeproc SORTS
 * the bibliography, so line N is not item N. An earlier version indexed by
 * position and attached the wrong confidence to the wrong citation, which
 * surfaced as a missing note rather than as an obviously wrong number.
 */
type RenderedEntry = { text: string; confidence: number | null; index: number };

type CSLEngine = {
  updateItems: (ids: string[]) => void;
  makeBibliography: () => Array<Record<string, unknown>>;
  setOutputFormat: (mode: "html" | "text" | "rtf") => void;
};

/**
 * Build an engine and render every entry.
 *
 * citeproc's calling convention, established by probing the library rather than
 * from its README, which describes none of this:
 *
 *   - `updateItems` takes an array of ITEM IDS, not item objects. Passing objects
 *     makes the registry call `retrieveItem` with a stringified object -- literally
 *     "[object Object]" -- which returns null and then fails on `.language`.
 *   - `retrieveItem` must be able to return the item. Returning null for an id it
 *     asks about is what produces `Cannot read properties of null (reading
 *     'language')`, an error that names the locale and points away from the
 *     registry. Three wrong fixes followed, each assuming the locale was at
 *     fault: a locale code, a JSON bundle, and a hand-built locale object.
 *   - `setOutputFormat` accepts only "html", "text" and "rtf". "bibtex" is not a
 *     mode; there is no BibTeX output format, so BibTeX is built from the styled
 *     HTML here.
 *   - `makeBibliography` returns a mix: one object of layout metadata whose
 *     `entry_ids` maps each rendered entry back to its item, then one object per
 *     rendered line keyed by its index. A consumer that reads the first object as
 *     a citation gets metadata, not a citation.
 */
async function renderEntries(run: RunResult, style: CitationStyle): Promise<RenderedEntry[]> {
  const entries = collectCiteable(run);
  if (entries.length === 0) return [];

  const items = entries.map(toCslItem);
  const byId = new Map(items.map((item) => [item.id as string, item]));

  const [{ default: CSL }, styleText, localeXml] = await Promise.all([
    import("citeproc"),
    loadStyle(style),
    loadLocale(),
  ]);

  const engine = new CSL.Engine(
    {
      retrieveLocale: () => localeXml,
      retrieveItem: (id: string) => byId.get(id) ?? null,
    } as never,
    styleText,
    LOCALE,
  ) as unknown as CSLEngine;

  engine.setOutputFormat("html");
  engine.updateItems(items.map((item) => item.id as string));

  const bibliography = engine.makeBibliography();
  const layout = bibliography[0] as { entry_ids?: string[][] } | undefined;
  const idOrder = (layout?.entry_ids ?? []).map((ids) => ids[0]);
  const confidenceById = new Map(
    items.map((item, i) => [item.id as string, entries[i]?.confidence ?? null]),
  );
  const indexById = new Map(items.map((item, i) => [item.id as string, i]));

  // citeproc returns the layout object first, then a SECOND object whose keys are
  // the line indexes and whose values are the rendered lines -- not one object
  // per line. An earlier version mapped `bibliography.slice(1)` as if it were
  // one object per entry, so a two-paper run produced one citation carrying the
  // first line's text and silently dropped the second. A test asserting "one
  // BibTeX entry per paper" caught it: 1 where 2 were expected.
  const lines: string[] = [];
  for (const obj of bibliography.slice(1)) {
    for (const key of Object.keys(obj).sort((a, b) => Number(a) - Number(b))) {
      lines.push(String(obj[key] ?? ""));
    }
  }

  return lines.map((line, i) => {
    const id = idOrder[i];
    const confidence = id ? (confidenceById.get(id) ?? null) : null;
    let text = line
      .replace(/<div class="csl-entry">/gi, "")
      .replace(/<\/div>/gi, "")
      .trim();
    if (confidence !== null && confidence < LOW_CONFIDENCE_THRESHOLD) {
      text += lowConfidenceNote(confidence);
    }
    return { text, confidence, index: id ? (indexById.get(id) ?? i) : i };
  });
}

function stripHtml(html: string): string {
  return html
    .replace(/<[^>]+>/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, " ")
    .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(Number(code)))
    .replace(/\s+/g, " ")
    .trim();
}

const RIS_TYPES: Record<string, string> = {
  "article-journal": "JOUR",
  "article-magazine": "MGZN",
  "article-newspaper": "NEWS",
  "paper-conference": "CPAPER",
  thesis: "THES",
  report: "RPRT",
  book: "BOOK",
  chapter: "CHAP",
  webpage: "ELEC",
};

function toRis(entries: CiteablePaper[]): string {
  return (
    entries
      .map(({ paper, confidence }) => {
        const lines: string[] = [`TY  - ${RIS_TYPES[cslType(paper)] ?? "JOUR"}`];
        for (const author of paper.authors ?? []) {
          const split = splitAuthor(author);
          if (split) {
            lines.push(
              split.given ? `AU  - ${split.family}, ${split.given}` : `AU  - ${split.family}`,
            );
          }
        }
        if (paper.title) lines.push(`TI  - ${paper.title}`);
        if (paper.journal) lines.push(`JO  - ${paper.journal}`);
        if (paper.year) lines.push(`PY  - ${paper.year}`);
        if (paper.doi) {
          lines.push(`DO  - ${paper.doi}`);
          lines.push(`UR  - https://doi.org/${paper.doi}`);
        }
        if (paper.abstract) lines.push(`AB  - ${paper.abstract.replace(/\s+/g, " ")}`);
        if (confidence !== null && confidence < LOW_CONFIDENCE_THRESHOLD) {
          lines.push(
            `N1  - Linked to the seed paper with low confidence (${confidence.toFixed(2)}). Verify this citation before relying on it.`,
          );
        }
        lines.push("ER  - ");
        return lines.join("\n");
      })
      .join("\n\n") + "\n"
  );
}

/** BibTeX built from the styled entries, one entry per paper. */
async function toBibtex(run: RunResult, style: CitationStyle): Promise<string> {
  const entries = collectCiteable(run);
  const rendered = await renderEntries(run, style);

  return rendered
    .map((entry) => {
      const paper = entries[entry.index]?.paper;
      const tags: string[] = [];
      const push = (key: string, value: string | null | undefined) => {
        if (value) tags.push(`  ${key} = {${value}}`);
      };

      push("title", paper?.title);
      if (paper?.authors?.length) {
        // BibTeX wants "and" as the name separator, which is the one thing CSL
        // deliberately does not emit.
        const names = paper.authors
          .map(splitAuthor)
          .filter((a): a is { family: string; given?: string } => a !== null)
          .map((a) => (a.given ? `${a.family}, ${a.given}` : a.family));
        if (names.length) tags.push(`  author = {${names.join(" and ")}}`);
      }
      push("journal", paper?.journal);
      if (paper?.year) tags.push(`  year = {${paper.year}}`);
      push("doi", paper?.doi);
      if (paper?.doi) tags.push(`  url = {https://doi.org/${paper.doi}}`);

      const id = paper?.paper_id || `paper-${entry.index + 1}`;
      // Prefer the DOI as the citation key -- it is the handle a reader
      // recognises -- but fall back to the unique paper_id when it is absent.
      const citeKey = (paper?.doi || id).replace(/[^A-Za-z0-9]/g, "_");
      const noteLine =
        entry.confidence !== null && entry.confidence < LOW_CONFIDENCE_THRESHOLD
          ? `\n  note = {Linked to the seed paper with low confidence (${entry.confidence.toFixed(
              2,
            )}). Verify this citation before relying on it.}`
          : "";
      return `@article{${citeKey},\n${tags.join(",\n")}${noteLine}\n}`;
    })
    .join("\n\n");
}

/** The public entry point: a run in, a downloadable file body out. */
export async function exportCitations(
  run: RunResult,
  style: CitationStyle,
  format: CitationFormat,
): Promise<{ filename: string; body: string; mime: string }> {
  const stem = `citegraph-${run.run_id}-${style}`;

  if (format === "ris") {
    return {
      filename: `${stem}.ris`,
      body: toRis(collectCiteable(run)),
      mime: "application/x-research-info-systems",
    };
  }

  return {
    filename: `${stem}.bib`,
    body: await toBibtex(run, style),
    mime: "application/x-bibtex",
  };
}

/** The styled citation list, for on-screen preview. */
export async function previewCitations(run: RunResult, style: CitationStyle): Promise<string[]> {
  return (await renderEntries(run, style)).map((entry) => stripHtml(entry.text));
}

/** Count of entries that will carry a low-confidence note, for the UI. */
export function lowConfidenceCount(run: RunResult): number {
  return collectCiteable(run).filter(
    (e) => e.confidence !== null && e.confidence < LOW_CONFIDENCE_THRESHOLD,
  ).length;
}
