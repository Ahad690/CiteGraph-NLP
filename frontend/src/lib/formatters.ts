import type { ConfidenceLevel, Paper, PopulationCandidate, PopulationResolution, CitationEdge, RunResult } from "@/types/api";

export function formatNumber(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString("en-US");
}

export function formatConfidence(score?: number | null): string {
  if (score == null) return "—";
  return `${Math.round(score * 100)}%`;
}

export function getConfidenceLevel(score?: number | null): ConfidenceLevel | "missing" {
  if (score == null) return "missing";
  if (score >= 0.75) return "high";
  if (score >= 0.45) return "medium";
  return "low";
}

export function getConfidenceColor(score?: number | null): string {
  const lvl = getConfidenceLevel(score);
  switch (lvl) {
    case "high": return "var(--accent-emerald)";
    case "medium": return "var(--accent-amber)";
    case "low": return "var(--accent-rose)";
    default: return "#64748b";
  }
}

export function truncateTitle(title: string, length = 70): string {
  if (!title) return "";
  return title.length > length ? title.slice(0, length - 1) + "…" : title;
}

export function getPaperById(papers: Paper[], paperId: string): Paper | undefined {
  return papers.find((p) => p.paper_id === paperId);
}

export function getPopulationForPaper(run: RunResult, paperId: string): PopulationResolution | undefined {
  return run.population_resolutions.find((p) => p.paper_id === paperId);
}

export function getCandidatesForPaper(run: RunResult, paperId: string): PopulationCandidate[] {
  return run.population_candidates.filter((c) => c.paper_id === paperId);
}

export function getEdgesForPaper(run: RunResult, paperId: string): CitationEdge[] {
  return run.citation_edges.filter((e) => e.source_paper_id === paperId || e.target_paper_id === paperId);
}

export function formatRelativeTime(iso: string): string {
  try {
    const d = new Date(iso);
    const diff = Date.now() - d.getTime();
    const sec = Math.floor(diff / 1000);
    if (sec < 60) return `${sec}s ago`;
    const min = Math.floor(sec / 60);
    if (min < 60) return `${min}m ago`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return `${hr}h ago`;
    return d.toLocaleDateString();
  } catch {
    return iso;
  }
}

export function formatAuthors(authors: string[], max = 3): string {
  if (!authors?.length) return "Unknown";
  if (authors.length <= max) return authors.join(", ");
  return `${authors.slice(0, max).join(", ")} +${authors.length - max}`;
}
