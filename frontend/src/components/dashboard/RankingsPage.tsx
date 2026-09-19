import { useMemo, useState } from "react";
import type { Paper, RunResult } from "@/types/api";
import { Trophy, Network, Copy, AlertTriangle } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { toast } from "sonner";
import { ConfidenceBadge } from "@/components/ui-kit/ConfidenceBadge";
import { PaperDetailDrawer } from "./PaperDetailDrawer";
import { getPaperById, getPopulationForPaper, formatNumber, formatConfidence, formatAuthors } from "@/lib/formatters";

export function RankingsPage({ run }: { run: RunResult }) {
  const seedDomain = run.papers.find((paper) => paper.paper_id === run.seed_paper_id)?.research_domain;
  const technicalSeed = seedDomain === "computer_science";
  const structuralSeed = technicalSeed || seedDomain === "nonclinical";
  const [minScore, setMinScore] = useState(0);
  const [highOnly, setHighOnly] = useState(false);
  const [hasPop, setHasPop] = useState(false);
  const [paper, setPaper] = useState<Paper | null>(null);

  const items = useMemo(() => {
    return run.ranked_foundational_papers.filter((r) => {
      if (r.score < minScore) return false;
      const pop = getPopulationForPaper(run, r.paper_id);
      const technical = run.technical_evidence.find((item) => item.paper_id === r.paper_id);
      if (highOnly && (technicalSeed ? (technical?.confidence ?? 0) : (pop?.confidence ?? 0)) < 0.75) return false;
      if (hasPop && (technicalSeed ? technical?.value == null : pop?.n_eff == null)) return false;
      return true;
    });
  }, [run, minScore, highOnly, hasPop, technicalSeed]);

  return (
    <div className="space-y-5">
      <div className="glass rounded-3xl p-6 lg:p-8 relative overflow-hidden">
        <div className="absolute -top-20 -left-20 h-56 w-56 rounded-full bg-purple/20 blur-3xl" />
        <div className="relative">
          <div className="flex items-center gap-2 mb-2">
            <Trophy className="h-5 w-5 text-purple" />
            <span className="label-tiny">Ranking</span>
          </div>
          <h1 className="text-[28px] font-bold tracking-tight text-text-primary">Top Probable Foundational Papers</h1>
          <p className="text-sm text-text-secondary mt-2 max-w-3xl">
            {structuralSeed ? "For nonclinical seeds, rankings use citation structure and age; technical counts are shown separately and do not influence scores." : "These papers are ranked using citation position, graph connectivity, clinical population evidence, source metrics, and confidence scores."}
          </p>
          <div className="mt-4 rounded-2xl bg-amber/10 border border-amber/30 p-3 flex items-start gap-2 text-xs text-amber max-w-3xl">
            <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>This ranking estimates probable foundational papers. It does not guarantee discovery of the absolute first or original paper.</span>
          </div>
        </div>
      </div>

      <div className="glass rounded-2xl p-4 grid md:grid-cols-3 gap-3">
        <div>
          <div className="label-tiny mb-1.5">Min score</div>
          <input type="range" min={0} max={1} step={0.05} value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} className="w-full accent-indigo" />
          <div className="text-xs text-text-secondary font-mono">{formatConfidence(minScore)}</div>
        </div>
        {!structuralSeed || technicalSeed ? <label className="flex items-end gap-2 text-sm text-text-secondary">
          <input type="checkbox" checked={highOnly} onChange={(e) => setHighOnly(e.target.checked)} className="h-4 w-4 accent-indigo" /> High-confidence only
        </label> : null}
        {!structuralSeed || technicalSeed ? <label className="flex items-end gap-2 text-sm text-text-secondary">
          <input type="checkbox" checked={hasPop} onChange={(e) => setHasPop(e.target.checked)} className="h-4 w-4 accent-indigo" /> {technicalSeed ? "Has dataset evidence" : "Has population evidence"}
        </label> : null}
      </div>

      <div className="space-y-3">
        {items.map((r, i) => {
          const paperItem = getPaperById(run.papers, r.paper_id);
          if (!paperItem) return null;
          const pop = getPopulationForPaper(run, r.paper_id);
          const technical = run.technical_evidence.find((item) => item.paper_id === r.paper_id);
          const isTop3 = i < 3;
          return (
            <div
              key={r.paper_id}
              className={`relative rounded-2xl p-5 lg:p-6 ${isTop3 ? "p-[1.5px] gradient-brand" : ""}`}
            >
              <div className={`${isTop3 ? "rounded-[calc(1rem-1px)] glass-strong p-5 lg:p-6" : "glass"} ${isTop3 ? "" : "rounded-2xl"}`}>
                <div className="flex flex-col lg:flex-row lg:items-start gap-5">
                  {/* Rank + score */}
                  <div className="flex items-center gap-4 lg:flex-col lg:items-start lg:w-32">
                    <div className={`h-14 w-14 rounded-2xl grid place-items-center font-bold text-2xl ${isTop3 ? "gradient-brand text-white shadow-lg glow-indigo" : "bg-surface-strong border border-border text-text-secondary"}`}>
                      {r.rank}
                    </div>
                    <div className="lg:mt-2">
                      <div className="label-tiny">Score</div>
                      <div className="text-xl font-bold text-text-primary font-mono">{formatConfidence(r.score)}</div>
                      {/* Score meter */}
                      <div className="mt-2 h-1.5 w-24 rounded-full bg-surface-hover overflow-hidden">
                        <div className="h-full gradient-brand rounded-full" style={{ width: `${r.score * 100}%` }} />
                      </div>
                    </div>
                  </div>

                  <div className="flex-1 min-w-0">
                    <button onClick={() => setPaper(paperItem)} className="text-left">
                      <h3 className="text-lg font-bold text-text-primary leading-snug hover:text-cyan transition-colors">{paperItem.title}</h3>
                    </button>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-text-muted mt-1.5">
                      <span>{paperItem.year ?? "—"}</span>
                      <span>·</span>
                      <span className="italic">{paperItem.journal ?? "—"}</span>
                      <span>·</span>
                      <span>{formatAuthors(paperItem.authors, 4)}</span>
                    </div>

                    <div className="grid sm:grid-cols-3 gap-2 mt-4">
                      <Stat label={technicalSeed ? "Dataset examples" : "Clinical N_eff"} value={structuralSeed && !technicalSeed ? "N/A" : formatNumber(technicalSeed ? technical?.value : pop?.n_eff)} />
                      <Stat label="Citations" value={formatNumber(paperItem.citation_count)} />
                      <Stat label="Confidence" valueNode={<ConfidenceBadge score={structuralSeed && !technicalSeed ? null : technicalSeed ? technical?.confidence : pop?.confidence} />} />
                    </div>

                    {r.explanation && (
                      <div className="mt-4 px-3 py-2.5 rounded-xl bg-surface-strong/50 border border-border text-sm text-text-secondary">
                        {r.explanation}
                      </div>
                    )}
                    {r.evidence_summary && (
                      <div className="mt-2 text-xs text-text-muted">
                        <span className="font-semibold text-text-secondary">Evidence summary: </span>{r.evidence_summary}
                      </div>
                    )}

                    <div className="flex flex-wrap gap-2 mt-4">
                      <Link to="/graph/$runId" params={{ runId: run.run_id }} className="inline-flex items-center gap-2 h-9 px-3 rounded-lg bg-surface-strong/60 border border-border hover:bg-surface-hover text-xs font-semibold text-text-secondary">
                        <Network className="h-3.5 w-3.5" /> View in graph
                      </Link>
                      <button
                        onClick={async () => {
                          const text = r.explanation || "";
                          try {
                            if (!navigator.clipboard) throw new Error("Clipboard API unavailable");
                            await navigator.clipboard.writeText(text);
                            toast.success("Explanation copied");
                          } catch (err) {
                            toast.error("Couldn't copy to clipboard", {
                              description: "Clipboard access was denied or unavailable.",
                            });
                            // eslint-disable-next-line no-console
                            console.warn("Clipboard copy failed:", err);
                          }
                        }}
                        className="inline-flex items-center gap-2 h-9 px-3 rounded-lg bg-surface-strong/60 border border-border hover:bg-surface-hover text-xs font-semibold text-text-secondary"
                      >
                        <Copy className="h-3.5 w-3.5" /> Copy explanation
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <PaperDetailDrawer paper={paper} run={run} onClose={() => setPaper(null)} />
    </div>
  );
}

function Stat({ label, value, valueNode }: { label: string; value?: string; valueNode?: React.ReactNode }) {
  return (
    <div className="rounded-xl bg-surface-strong/40 border border-border px-3 py-2">
      <div className="label-tiny">{label}</div>
      <div className="text-sm font-semibold text-text-primary mt-0.5">{valueNode ?? value ?? "—"}</div>
    </div>
  );
}
