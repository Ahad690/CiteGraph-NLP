import { useMemo, useState } from "react";
import type { CitationEdge, Paper, RunResult } from "@/types/api";
import { CitationGraph, type GraphFilters } from "@/components/graph/CitationGraph";
import { PaperDetailDrawer } from "./PaperDetailDrawer";
import { getPaperById, formatConfidence } from "@/lib/formatters";
import { X } from "lucide-react";

export function CitationGraphPage({ run }: { run: RunResult }) {
  const years = run.papers.map((p) => p.year ?? 2000);
  const minY = Math.min(...years, 2000);
  const maxY = Math.max(...years, new Date().getFullYear());

  const [filters, setFilters] = useState<GraphFilters>({
    minConfidence: 0,
    minWeight: 0,
    yearRange: [minY, maxY],
    seedConnectedOnly: false,
    hideMissing: false,
    highConfOnly: false,
    highlightFoundational: true,
  });
  const [paper, setPaper] = useState<Paper | null>(null);
  const [edge, setEdge] = useState<CitationEdge | null>(null);

  const reset = () => setFilters({
    minConfidence: 0, minWeight: 0, yearRange: [minY, maxY],
    seedConnectedOnly: false, hideMissing: false, highConfOnly: false, highlightFoundational: true,
  });

  return (
    <div className="space-y-4">
      <div className="grid lg:grid-cols-[280px_1fr] gap-4">
        {/* Filters */}
        <div className="glass rounded-2xl p-4 space-y-4 lg:sticky lg:top-[92px] self-start">
          <h3 className="text-sm font-semibold text-text-primary">Graph filters</h3>
          <Slider label="Min edge confidence" value={filters.minConfidence} onChange={(v) => setFilters({ ...filters, minConfidence: v })} />
          <Slider label="Min edge weight" value={filters.minWeight} onChange={(v) => setFilters({ ...filters, minWeight: v })} />
          <div>
            <div className="label-tiny mb-2">Year range</div>
            <div className="flex items-center gap-2">
              <input type="number" value={filters.yearRange[0]} onChange={(e) => setFilters({ ...filters, yearRange: [Number(e.target.value), filters.yearRange[1]] })} className="w-full h-9 px-2 rounded-lg bg-surface-strong/60 border border-border text-sm text-text-primary" />
              <span className="text-text-muted">–</span>
              <input type="number" value={filters.yearRange[1]} onChange={(e) => setFilters({ ...filters, yearRange: [filters.yearRange[0], Number(e.target.value)] })} className="w-full h-9 px-2 rounded-lg bg-surface-strong/60 border border-border text-sm text-text-primary" />
            </div>
          </div>
          <Check label="Only seed-connected" value={filters.seedConnectedOnly} onChange={(v) => setFilters({ ...filters, seedConnectedOnly: v })} />
          <Check label="Hide missing population" value={filters.hideMissing} onChange={(v) => setFilters({ ...filters, hideMissing: v })} />
          <Check label="High-confidence only" value={filters.highConfOnly} onChange={(v) => setFilters({ ...filters, highConfOnly: v })} />
          <Check label="Highlight foundational" value={filters.highlightFoundational} onChange={(v) => setFilters({ ...filters, highlightFoundational: v })} />
          <button onClick={reset} className="w-full h-10 rounded-xl bg-surface-strong/60 border border-border hover:bg-surface-hover text-sm font-semibold text-text-primary">Reset filters</button>
        </div>

        <div className="h-[680px] lg:h-[720px]">
          <CitationGraph
            run={run}
            filters={filters}
            onSelectPaper={setPaper}
            onSelectEdge={setEdge}
          />
        </div>
      </div>

      <PaperDetailDrawer paper={paper} run={run} onClose={() => setPaper(null)} />
      {edge && (
        <EdgeDetailPanel
          edge={edge}
          source={getPaperById(run.papers, edge.source_paper_id)}
          target={getPaperById(run.papers, edge.target_paper_id)}
          onClose={() => setEdge(null)}
        />
      )}
    </div>
  );
}

function Slider({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="label-tiny">{label}</span>
        <span className="text-xs text-text-secondary font-mono">{formatConfidence(value)}</span>
      </div>
      <input type="range" min={0} max={1} step={0.05} value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-indigo" />
    </div>
  );
}

function Check({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2.5 cursor-pointer text-sm text-text-secondary hover:text-text-primary">
      <input type="checkbox" checked={value} onChange={(e) => onChange(e.target.checked)} className="h-4 w-4 accent-indigo rounded" />
      {label}
    </label>
  );
}

function EdgeDetailPanel({ edge, source, target, onClose }: { edge: CitationEdge; source?: Paper; target?: Paper; onClose: () => void }) {
  return (
    <div className="fixed bottom-4 right-4 z-40 w-[360px] glass-strong rounded-2xl border border-border-strong p-4 shadow-2xl animate-in slide-in-from-bottom-4 duration-200">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="label-tiny text-cyan">Citation edge</div>
        <button onClick={onClose} className="h-7 w-7 grid place-items-center rounded-lg hover:bg-surface-hover"><X className="h-3.5 w-3.5" /></button>
      </div>
      <div className="space-y-2 text-xs">
        <Row label="Source" value={source?.title} />
        <Row label="Target" value={target?.title} />
      </div>
      <div className="grid grid-cols-2 gap-2 mt-3">
        <Stat label="Final weight" value={edge.final_weight?.toFixed(2)} />
        <Stat label="Base weight" value={edge.base_weight?.toFixed(2)} />
        <Stat label="Confidence" value={formatConfidence(edge.confidence)} />
        <Stat label="N score" value={edge.n_score?.toFixed(2)} />
        <Stat label="Journal score" value={edge.journal_score?.toFixed(2)} />
        <Stat label="Providers" value={edge.providers?.join(", ")} />
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string }) {
  return (
    <div>
      <div className="label-tiny">{label}</div>
      <div className="text-text-secondary leading-snug mt-0.5">{value || "—"}</div>
    </div>
  );
}
function Stat({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="rounded-lg bg-surface-strong/50 border border-border px-2.5 py-2">
      <div className="label-tiny">{label}</div>
      <div className="text-xs font-mono text-text-primary mt-0.5">{value ?? "—"}</div>
    </div>
  );
}
