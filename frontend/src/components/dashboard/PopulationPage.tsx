import { useMemo, useState } from "react";
import type { PopulationResolution, RunResult, Paper } from "@/types/api";
import { ConfidenceBadge } from "@/components/ui-kit/ConfidenceBadge";
import { formatNumber, getCandidatesForPaper, getPaperById, truncateTitle, getConfidenceColor } from "@/lib/formatters";
import { X, Search } from "lucide-react";

const STATUS_STYLE: Record<string, { label: string; color: string; bg: string }> = {
  resolved: { label: "Resolved", color: "#34d399", bg: "rgba(16,185,129,0.12)" },
  ambiguous: { label: "Ambiguous", color: "#fbbf24", bg: "rgba(245,158,11,0.12)" },
  missing: { label: "Missing", color: "#94a3b8", bg: "rgba(148,163,184,0.12)" },
  low_confidence: { label: "Low confidence", color: "#fb7185", bg: "rgba(244,63,94,0.12)" },
};

export function PopulationPage({ run }: { run: RunResult }) {
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selected, setSelected] = useState<PopulationResolution | null>(null);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const rows = useMemo(() => {
    const ql = q.toLowerCase().trim();
    return run.population_resolutions.filter((r) => {
      if (statusFilter !== "all" && r.status !== statusFilter) return false;
      if (!ql) return true;
      const paper = getPaperById(run.papers, r.paper_id);
      return paper?.title.toLowerCase().includes(ql) || (r.evidence || "").toLowerCase().includes(ql);
    });
  }, [run, q, statusFilter]);

  const counts = useMemo(() => {
    const c = { resolved: 0, ambiguous: 0, missing: 0, low_confidence: 0 } as Record<string, number>;
    run.population_resolutions.forEach((r) => { c[r.status as string] = (c[r.status as string] || 0) + 1; });
    return c;
  }, [run]);

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {(["resolved", "ambiguous", "low_confidence", "missing"] as const).map((k) => {
          const s = STATUS_STYLE[k];
          return (
            <button
              key={k}
              onClick={() => setStatusFilter(statusFilter === k ? "all" : k)}
              className={`glass rounded-2xl p-4 text-left transition-all ${statusFilter === k ? "border-border-strong shadow-[0_0_24px_-6px_rgba(79,70,229,0.45)]" : ""}`}
            >
              <div className="label-tiny" style={{ color: s.color }}>{s.label}</div>
              <div className="text-2xl font-bold text-text-primary mt-1">{counts[k] || 0}</div>
            </button>
          );
        })}
      </div>

      <div className="glass rounded-2xl p-4 flex items-center gap-3">
        <div className="flex items-center gap-2 px-3 h-10 rounded-xl bg-surface-strong/60 border border-border flex-1">
          <Search className="h-4 w-4 text-text-muted" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search title or evidence text…"
            className="bg-transparent outline-none text-sm text-text-primary w-full placeholder:text-text-muted"
          />
        </div>
        <button onClick={() => setStatusFilter("all")} className="text-xs text-text-muted hover:text-text-primary">Show all</button>
      </div>

      <div className="glass rounded-2xl overflow-hidden">
        <div className="hidden lg:grid grid-cols-[1fr_100px_140px_120px_120px_120px] gap-3 px-4 py-3 border-b border-border text-[11px] uppercase tracking-wider text-text-muted font-semibold">
          <span>Paper</span>
          <span>N_eff</span>
          <span>Semantic type</span>
          <span>Section</span>
          <span>Status</span>
          <span>Confidence</span>
        </div>
        <div className="divide-y divide-border">
          {rows.map((r) => {
            const paper = getPaperById(run.papers, r.paper_id);
            const status = STATUS_STYLE[r.status as string] || STATUS_STYLE.missing;
            const expanded = expandedRow === r.paper_id;
            return (
              <div key={r.paper_id} className="hover:bg-surface-hover/30 transition-colors">
                <button
                  onClick={() => setSelected(r)}
                  className="w-full text-left grid grid-cols-1 lg:grid-cols-[1fr_100px_140px_120px_120px_120px] gap-3 px-4 py-3.5"
                >
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-text-primary">{truncateTitle(paper?.title || "Unknown paper", 90)}</div>
                    {r.evidence && (
                      <div
                        onClick={(e) => { e.stopPropagation(); setExpandedRow(expanded ? null : r.paper_id); }}
                        className="text-xs text-text-muted italic mt-1 cursor-pointer hover:text-text-secondary"
                      >
                        "{expanded || r.evidence.length <= 180 ? r.evidence : r.evidence.slice(0, 180) + "…"}"
                      </div>
                    )}
                    {r.explanation && expanded && (
                      <div className="text-[11px] text-text-secondary mt-2 px-3 py-2 rounded-lg bg-surface-strong/40 border border-border">{r.explanation}</div>
                    )}
                  </div>
                  <div className="text-sm font-mono font-semibold text-text-primary">{formatNumber(r.n_eff)}</div>
                  <div className="text-[11px] text-text-secondary font-mono">{r.semantic_type || "—"}</div>
                  <div className="text-xs text-text-secondary">{r.section || "—"}</div>
                  <div>
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold" style={{ background: status.bg, color: status.color }}>
                      {status.label}
                    </span>
                  </div>
                  <div><ConfidenceBadge score={r.confidence} /></div>
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {selected && <CandidateDrawer resolution={selected} run={run} onClose={() => setSelected(null)} />}
    </div>
  );
}

function CandidateDrawer({ resolution, run, onClose }: { resolution: PopulationResolution; run: RunResult; onClose: () => void }) {
  const paper = getPaperById(run.papers, resolution.paper_id);
  const candidates = getCandidatesForPaper(run, resolution.paper_id);

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full md:w-[520px] h-full glass-strong border-l border-border-strong overflow-y-auto scrollbar-thin animate-in slide-in-from-right duration-200">
        <div className="sticky top-0 glass-strong border-b border-border px-5 py-4 flex items-center justify-between">
          <div className="label-tiny">Population candidates</div>
          <button onClick={onClose} className="h-9 w-9 grid place-items-center rounded-xl bg-surface-strong/80 border border-border hover:bg-surface-hover"><X className="h-4 w-4" /></button>
        </div>
        <div className="px-5 py-5 space-y-5">
          <div>
            <h2 className="text-base font-bold text-text-primary leading-snug">{paper?.title || "Unknown paper"}</h2>
            <div className="text-xs text-text-muted mt-1">{paper?.year} · {paper?.journal}</div>
          </div>

          <div className="rounded-2xl border border-border bg-surface-strong/50 p-4">
            <div className="label-tiny mb-1">Selected N_eff</div>
            <div className="flex items-baseline gap-3">
              <div className="text-3xl font-bold text-text-primary">{formatNumber(resolution.n_eff)}</div>
              <ConfidenceBadge score={resolution.confidence} />
            </div>
            {resolution.semantic_type && <div className="text-xs text-text-muted font-mono mt-1">{resolution.semantic_type}</div>}
            {resolution.explanation && (
              <div className="mt-3 px-3 py-2 rounded-lg bg-amber/8 border border-amber/25 text-xs text-text-secondary">
                {resolution.status === "ambiguous" && <span className="font-semibold text-amber">Ambiguous · </span>}
                {resolution.explanation}
              </div>
            )}
          </div>

          <div>
            <div className="label-tiny mb-3">All candidate values ({candidates.length})</div>
            <div className="space-y-3">
              {candidates.length === 0 ? (
                <div className="text-sm text-text-muted">No candidate evidence available. Metadata coverage may be incomplete.</div>
              ) : candidates.map((c) => (
                <div key={c.candidate_id} className="rounded-2xl border border-border bg-surface-strong/40 p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="text-xl font-bold text-text-primary font-mono">{formatNumber(c.value)}</div>
                    <ConfidenceBadge score={c.confidence} />
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-text-muted">
                    {c.semantic_type && <span className="font-mono">{c.semantic_type}</span>}
                    {c.section && <><span>·</span><span>{c.section}</span></>}
                    {c.extraction_method && <><span>·</span><span className="font-mono">{c.extraction_method}</span></>}
                  </div>
                  {c.sentence && <div className="text-xs text-text-secondary italic leading-relaxed">"{c.sentence}"</div>}
                  {/* Confidence meter */}
                  <div className="h-1.5 w-full rounded-full bg-surface-hover overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${(c.confidence ?? 0) * 100}%`, backgroundColor: getConfidenceColor(c.confidence) }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
