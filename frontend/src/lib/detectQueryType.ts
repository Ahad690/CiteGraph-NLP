/**
 * Work out what kind of identifier the user pasted.
 *
 * This mirrors `detect_query_type` in src/citegraph/utils/ids.py, branch for
 * branch. It exists so the badge under the input updates as you type without a
 * round-trip; the server runs its own copy and is the authority, because a
 * client can be stale or bypassed entirely.
 *
 * Keep the two in step. If a branch changes here it changes there.
 */

export type QueryType = "doi" | "pmid" | "pmcid" | "title" | "url";

// A DOI is a "10." prefix, a registrant code, "/", then a suffix.
const DOI_RE = /^10\.\d{4,9}\/\S+$/;
const PMCID_RE = /^PMC\d+$/;
const PMID_RE = /^\d{1,9}$/;
const OPENALEX_RE = /^W\d+$/;

export function detectQueryType(value: string): QueryType {
  const text = (value ?? "").trim();
  if (!text) return "title";

  const lowered = text.toLowerCase();

  // A URL first: a publisher URL often contains a DOI, and the server's URL
  // resolver knows how to pull it out and strip view segments like /full.
  if (
    lowered.startsWith("http://") ||
    lowered.startsWith("https://") ||
    lowered.startsWith("www.")
  ) {
    return "url";
  }

  if (PMCID_RE.test(text.toUpperCase().replace("PMCID:", "").trim())) {
    return "pmcid";
  }

  let candidate = text;
  for (const prefix of ["doi:", "doi "]) {
    if (lowered.startsWith(prefix)) {
      candidate = text.slice(prefix.length).trim();
      break;
    }
  }
  if (DOI_RE.test(candidate)) return "doi";

  if (PMID_RE.test(text.toUpperCase().replace("PMID:", "").trim())) {
    return "pmid";
  }

  // An OpenAlex work id goes down the providers' DOI path.
  if (OPENALEX_RE.test(text.toUpperCase())) return "doi";

  // Free text is the only input with no distinguishing shape, so anything
  // unrecognised is better searched than rejected.
  return "title";
}

/** What the badge says, and what the hint under the field explains. */
export const QUERY_TYPE_LABELS: Record<QueryType, { label: string; hint: string }> = {
  doi: { label: "DOI", hint: "Digital Object Identifier. The most precise way to search." },
  pmid: { label: "PubMed ID", hint: "Numeric PubMed identifier." },
  pmcid: { label: "PMC ID", hint: "PubMed Central identifier." },
  url: { label: "URL", hint: "The page will be read for a DOI or PubMed identifier." },
  title: {
    label: "Title",
    hint: "Searched by title. Less precise than a DOI: papers can share a title.",
  },
};
