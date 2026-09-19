import { X, ExternalLink, Copy } from "lucide-react";
import { toast } from "sonner";
import type { Paper, RunResult } from "@/types/api";
import { ConfidenceBadge } from "../ui-kit/ConfidenceBadge";
import { RoleBadge } from "../ui-kit/RoleBadge";
import { formatNumber, formatAuthors, getPopulationForPaper, getEdgesForPaper } from "@/lib/formatters";

interface Props {
  paper: Paper | null;
  run: RunResult;
  onClose: () => void;
}

export function PaperDetailDrawer({ paper, run, onClose }: Props) {
  if (!paper) return null;
  const isSeed = paper.paper_id === run.seed_paper_id;
  const isFoundational = run.ranked_foundational_papers.some((r) => r.paper_id === paper.paper_id);
  const population = getPopulationForPaper(run, paper.paper_id);
  const technical = run.technical_evidence.find((item) => item.paper_id === paper.paper_id);
  const edges = getEdgesForPaper(run, paper.paper_id);

  const copy = (text: string, label: string) => {
    navigator.clipboard?.writeText(text)
      .then(() => toast.success(`${label} copied`))
      .catch(() => toast.error(`Failed to copy ${label}`));
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200" onClick={onClose} />
      <div className="relative w-full md:w-[480px] h-full glass-strong border-l border-border-strong overflow-y-auto scrollbar-thin animate-in slide-in-from-right duration-200">
        <div className="sticky top-0 z-10 glass-strong border-b border-border px-5 py-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {isSeed && <RoleBadge role="seed" />}
            {isFoundational && <RoleBadge role="foundational" />}
            {!isSeed && !isFoundational && <RoleBadge role="cited" />}
          </div>
          <button onClick={onClose} className="h-9 w-9 grid place-items-center rounded-xl bg-surface-strong/80 border border-border hover:bg-surface-hover">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-5 py-5 space-y-5">
          <div>
            <h2 className="text-lg font-bold text-text-primary leading-snug">{paper.title}</h2>
            <p className="text-sm text-text-secondary mt-2">{formatAuthors(paper.authors, 8)}</p>
            <div className="flex flex-wrap items-center gap-2 mt-3 text-xs text-text-muted">
              {paper.year && <span>{paper.year}</span>}
              {paper.year && paper.journal && <span className="opacity-50">·</span>}
              {paper.journal && <span className="italic">{paper.journal}</span>}
              {paper.research_field && <span>· {paper.research_field} (OpenAlex)</span>}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Stat label="Citation count" value={formatNumber(paper.citation_count)} />
            <Stat label="Connected edges" value={String(edges.length)} />
            <Stat label="Metadata confidence" value={paper.metadata_confidence != null ? `${Math.round(paper.metadata_confidence * 100)}%` : "—"} />
            <Stat label={technical ? "Dataset examples" : "Population N_eff"} value={technical ? formatNumber(technical.value) : population?.status === "not_applicable" ? "N/A" : formatNumber(population?.n_eff)} />
          </div>

          {paper.abstract && (
            <div>
              <div className="label-tiny mb-2">Abstract</div>
              <p className="text-sm text-text-secondary leading-relaxed">{paper.abstract}</p>
            </div>
          )}

          <div className="space-y-2">
            <div className="label-tiny">Identifiers</div>
            {paper.doi && (
              <Row label="DOI" value={paper.doi} action={
                <div className="flex gap-1">
                  <button onClick={() => copy(paper.doi!, "DOI")} className="h-7 w-7 grid place-items-center rounded-lg hover:bg-surface-hover" aria-label="Copy DOI"><Copy className="h-3.5 w-3.5" /></button>
                  <a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noreferrer" className="h-7 w-7 grid place-items-center rounded-lg hover:bg-surface-hover" aria-label="Open DOI"><ExternalLink className="h-3.5 w-3.5" /></a>
                </div>
              } />
            )}
            {paper.pmid && <Row label="PMID" value={paper.pmid} />}
            {paper.pmcid && <Row label="PMCID" value={paper.pmcid} />}
            {paper.arxiv_id && <Row label="arXiv" value={paper.arxiv_id} action={<a href={`https://arxiv.org/abs/${paper.arxiv_id}`} target="_blank" rel="noreferrer" className="h-7 w-7 grid place-items-center rounded-lg hover:bg-surface-hover" aria-label="Open arXiv paper"><ExternalLink className="h-3.5 w-3.5" /></a>} />}
          </div>

          {technical && (
            <div className="rounded-2xl border border-border bg-surface-strong/50 p-4 space-y-2">
              <div className="label-tiny">Computer-science dataset evidence</div>
              <div className="text-2xl font-bold text-text-primary">{formatNumber(technical.value)} {technical.unit ?? ""}</div>
              {technical.section && <div className="text-xs text-text-muted">Source: {technical.section.replaceAll("_", " ")}</div>}
              {technical.evidence && <p className="text-xs text-text-secondary italic">"{technical.evidence}"</p>}
              <p className="text-xs text-text-muted">{technical.explanation}</p>
            </div>
          )}

          {population && population.status !== "not_applicable" && (
            <div className="rounded-2xl border border-border bg-surface-strong/50 p-4 space-y-2">
              <div className="flex items-center justify-between">
                <div className="label-tiny">Population evidence</div>
                <ConfidenceBadge score={population.confidence} />
              </div>
              <div className="text-2xl font-bold text-text-primary">{formatNumber(population.n_eff)}</div>
              {population.semantic_type && <div className="text-xs text-text-muted font-mono">{population.semantic_type}</div>}
              {population.evidence && <p className="text-xs text-text-secondary italic mt-2 leading-relaxed">"{population.evidence}"</p>}
              {population.explanation && <p className="text-xs text-text-muted mt-2">{population.explanation}</p>}
            </div>
          )}

          {paper.source_ids && Object.keys(paper.source_ids).length > 0 && (
            <div>
              <div className="label-tiny mb-2">Source providers</div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(paper.source_ids).map(([k, v]) => (
                  <span key={k} className="px-2 py-1 rounded-lg bg-surface-strong/60 border border-border text-[11px] font-mono text-text-secondary">
                    {k}: {v}
                  </span>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={() => copy(`${paper.title}. ${formatAuthors(paper.authors, 99)}. ${paper.journal || ""} ${paper.year || ""}. ${paper.doi || ""}`, "Citation")}
            className="w-full h-10 rounded-xl bg-surface-strong/70 border border-border hover:bg-surface-hover text-sm font-semibold text-text-primary"
          >
            Copy citation metadata
          </button>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-surface-strong/50 border border-border p-3">
      <div className="label-tiny mb-1">{label}</div>
      <div className="text-base font-semibold text-text-primary">{value}</div>
    </div>
  );
}

function Row({ label, value, action }: { label: string; value: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2 px-3 h-10 rounded-xl bg-surface-strong/40 border border-border">
      <div className="text-[11px] uppercase tracking-wider text-text-muted font-semibold w-16 shrink-0">{label}</div>
      <div className="text-xs text-text-secondary font-mono truncate flex-1">{value}</div>
      {action}
    </div>
  );
}
