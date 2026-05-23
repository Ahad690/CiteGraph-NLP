export type RunStatus = "pending" | "running" | "processing" | "started" | "completed" | "failed";

export type SemanticType =
  | "TOTAL_RANDOMIZED"
  | "TOTAL_ANALYZED"
  | "TOTAL_ENROLLED"
  | "ARM_SIZE"
  | "SCREENED"
  | "COMPLETERS"
  | "EVENT_COUNT"
  | "FOLLOWUP_COUNT"
  | "SAMPLE_SIZE_GENERIC"
  | "UNKNOWN_NUMERIC";

export type PopulationStatus = "resolved" | "ambiguous" | "missing" | "low_confidence";

export type ConfidenceLevel = "high" | "medium" | "low";

export type ExportFormat = "json" | "csv" | "graphml" | "markdown";

export interface Paper {
  paper_id: string;
  title: string;
  doi?: string | null;
  pmid?: string | null;
  pmcid?: string | null;
  authors: string[];
  year?: number | null;
  journal?: string | null;
  abstract?: string | null;
  metadata_confidence?: number | null;
  citation_count?: number | null;
  source_ids?: Record<string, string>;
  provenance?: Record<string, unknown>;
}

export interface PopulationResolution {
  paper_id: string;
  study_id?: string;
  n_eff?: number | null;
  semantic_type?: SemanticType;
  confidence?: number | null;
  status: PopulationStatus | string;
  evidence?: string | null;
  section?: string | null;
  explanation?: string | null;
}

export interface PopulationCandidate {
  candidate_id: string;
  paper_id: string;
  value?: number | null;
  raw_text?: string;
  sentence?: string;
  section?: string;
  semantic_type?: SemanticType;
  confidence?: number | null;
  extraction_method?: string;
}

export interface CitationEdge {
  edge_id: string;
  source_paper_id: string;
  target_paper_id: string;
  confidence?: number | null;
  base_weight?: number | null;
  final_weight?: number | null;
  n_score?: number | null;
  journal_score?: number | null;
  providers?: string[];
}

export interface RankedFoundationalPaper {
  paper_id: string;
  rank: number;
  score: number;
  explanation?: string;
  evidence_summary?: string;
}

export interface RankedPath {
  rank: number;
  path_score: number;
  paper_ids: string[];
  edge_weights: number[];
  average_confidence: number;
  path_length: number;
  explanation?: string;
}

export interface RunResult {
  run_id: string;
  status: RunStatus;
  seed_paper_id: string;
  papers: Paper[];
  population_resolutions: PopulationResolution[];
  population_candidates: PopulationCandidate[];
  citation_edges: CitationEdge[];
  ranked_foundational_papers: RankedFoundationalPaper[];
  ranked_paths: RankedPath[];
  warnings: string[];
  created_at: string;
}

/** Minimal payload returned by GET /api/runs/{id} while a run is still
 *  in-progress or has failed — the backend omits papers/edges/etc. */
export interface RunStatusPayload {
  run_id: string;
  status: RunStatus;
  error?: string | null;
  created_at: string;
}

/** Raw payload returned by the backend for a run. The completed shape
 *  carries the full RunResult; the in-progress/failed shape only carries
 *  the RunStatusPayload fields. Components should normalize via
 *  `normalizeRun()` before consuming. */
export type RunPayload = RunResult | RunStatusPayload;
