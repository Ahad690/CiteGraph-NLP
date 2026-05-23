import { Fragment, useMemo, useState } from "react";
import type { Paper, RunResult } from "@/types/api";
import { ChevronRight } from "lucide-react";
import { ConfidenceBadge } from "@/components/ui-kit/ConfidenceBadge";
import { PaperDetailDrawer } from "./PaperDetailDrawer";
import { getPaperById, getPopulationForPaper, formatNumber, formatConfidence, truncateTitle } from "@/lib/formatters";
import { EmptyState } from "@/components/ui-kit/EmptyState";

export function CitationPathsPage({ run }: { run: RunResult }) {
  const [minScore, setMinScore] = useState(0);
  const [maxLength, setMaxLength] = useState(10);
  const [highOnly, setHighOnly] = useState(false);
  const [popOnly, setPopOnly] = useState(false);
  const [paper, setPaper] = useState<Paper | null>(null);

  const paths = useMemo(() => {
    return run.ranked_paths.filter((p) => {
      if (p.path_score < minScore) return false;
      if (p.path_length > maxLength) return false;
      if (highOnly && p.average_confidence < 0.75) return false;
      if (popOnly) {
        const hasPop = p.paper_ids.some((pid) => getPopulationForPaper(run, pid)?.n_eff != null);
        if (!hasPop) return false;
      }
      return true;
    });
  }, [run, minScore, maxLength, highOnly, popOnly]);

  return (
    <div className="space-y-5">
      <div className="glass rounded-2xl p-4 grid md:grid-cols-4 gap-3">
        <div>
          <div className="label-tiny mb-1.5">Min path score</div>
          <input type="range" min={0} max={1} step={0.05} value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} className="w-full accent-indigo" />
          <div className="text-xs text-text-secondary font-mono">{formatConfidence(minScore)}</div>
        </div>
        <div>
          <div className="label-tiny mb-1.5">Max path length</div>
          <input type="number" min={1} max={20} value={maxLength} onChange={(e) => setMaxLength(Number(e.target.value))} className="w-full h-9 px-2 rounded-lg bg-surface-strong/60 border border-border text-sm" />
        </div>
        <label className="flex items-end gap-2 text-sm text-text-secondary">
          <input type="checkbox" checked={highOnly} onChange={(e) => setHighOnly(e.target.checked)} className="h-4 w-4 accent-indigo" /> High-confidence only
        </label>
        <label className="flex items-end gap-2 text-sm text-text-secondary">
          <input type="checkbox" checked={popOnly} onChange={(e) => setPopOnly(e.target.checked)} className="h-4 w-4 accent-indigo" /> With population evidence
        </label>
      </div>

      {paths.length === 0 ? (
        <EmptyState title="No ranked citation paths available" description="Citation data may be incomplete or filters too strict." />
      ) : (
        <div className="space-y-4">
          {paths.map((p) => (
            <div key={p.rank} className="glass rounded-2xl p-5">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-xl gradient-brand-soft border border-border-strong grid place-items-center font-bold text-sm text-cyan">#{p.rank}</div>
                  <div>
                    <div className="text-sm font-semibold text-text-primary">Path score {formatConfidence(p.path_score)}</div>
                    <div className="text-xs text-text-muted">Avg confidence {formatConfidence(p.average_confidence)} · Length {p.path_length}</div>
                  </div>
                </div>
              </div>
              {p.explanation && <p className="text-sm text-text-secondary mb-4">{p.explanation}</p>}

              {/* Timeline */}
              <div className="flex flex-col lg:flex-row lg:items-stretch gap-2 lg:gap-0">
                {p.paper_ids.map((pid, idx) => {
                  const paperItem = getPaperById(run.papers, pid);
                  if (!paperItem) return null;
                  const pop = getPopulationForPaper(run, pid);
                  // Composite key: a paper can appear in multiple ranked paths
                  // (and theoretically at multiple positions in one path), so
                  // bare `pid` is not unique.
                  const itemKey = `${p.rank}-${idx}-${pid}`;
                  return (
                    <Fragment key={itemKey}>
                      <button
                        onClick={() => setPaper(paperItem)}
                        className="flex-1 min-w-0 text-left rounded-2xl bg-surface-strong/40 border border-border hover:border-border-strong p-3 transition-colors"
                      >
                        <div className="flex items-center gap-2 text-[11px] text-text-muted mb-1">
                          <span>{paperItem.year ?? "—"}</span>
                          {paperItem.journal && <><span>·</span><span className="italic truncate">{paperItem.journal}</span></>}
                        </div>
                        <div className="text-sm font-semibold text-text-primary leading-snug">{truncateTitle(paperItem.title, 60)}</div>
                        <div className="flex items-center gap-2 mt-2">
                          {pop?.n_eff != null && <span className="text-[11px] font-mono text-text-secondary">N={formatNumber(pop.n_eff)}</span>}
                          <ConfidenceBadge score={pop?.confidence} />
                        </div>
                      </button>
                      {idx < p.paper_ids.length - 1 && (
                        <div className="flex lg:flex-col items-center justify-center px-2 lg:px-3 gap-1">
                          <ChevronRight className="h-4 w-4 text-cyan rotate-90 lg:rotate-0" />
                          {p.edge_weights[idx] != null && (
                            <span className="text-[10px] font-mono text-text-muted">{p.edge_weights[idx].toFixed(2)}</span>
                          )}
                        </div>
                      )}
                    </Fragment>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      <PaperDetailDrawer paper={paper} run={run} onClose={() => setPaper(null)} />
    </div>
  );
}
