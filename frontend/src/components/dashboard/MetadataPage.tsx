import { useMemo, useState } from "react";
import type { Paper, RunResult } from "@/types/api";
import { Search, ArrowUpDown } from "lucide-react";
import { ConfidenceBadge } from "@/components/ui-kit/ConfidenceBadge";
import { RoleBadge } from "@/components/ui-kit/RoleBadge";
import { PaperDetailDrawer } from "./PaperDetailDrawer";
import { formatNumber, formatAuthors, truncateTitle } from "@/lib/formatters";
import { EmptyState } from "@/components/ui-kit/EmptyState";

type SortKey = "year" | "confidence" | "citations" | "title";

export function MetadataPage({ run }: { run: RunResult }) {
  const [q, setQ] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("year");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [seedOnly, setSeedOnly] = useState(false);
  const [hasDoiOnly, setHasDoiOnly] = useState(false);
  const [selected, setSelected] = useState<Paper | null>(null);

  const foundationalSet = new Set(run.ranked_foundational_papers.map((r) => r.paper_id));

  const rows = useMemo(() => {
    const ql = q.toLowerCase().trim();
    let r = run.papers.filter((p) => {
      if (seedOnly && p.paper_id !== run.seed_paper_id) return false;
      if (hasDoiOnly && !p.doi) return false;
      if (!ql) return true;
      return (
        p.title.toLowerCase().includes(ql) ||
        p.authors.some((a) => a.toLowerCase().includes(ql)) ||
        (p.journal || "").toLowerCase().includes(ql) ||
        (p.doi || "").toLowerCase().includes(ql)
      );
    });
    r = [...r].sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      switch (sortKey) {
        case "year": return ((a.year ?? 0) - (b.year ?? 0)) * dir;
        case "confidence": return ((a.metadata_confidence ?? 0) - (b.metadata_confidence ?? 0)) * dir;
        case "citations": return ((a.citation_count ?? 0) - (b.citation_count ?? 0)) * dir;
        case "title": return a.title.localeCompare(b.title) * dir;
      }
    });
    return r;
  }, [run, q, sortKey, sortDir, seedOnly, hasDoiOnly]);

  const toggleSort = (k: SortKey) => {
    if (sortKey === k) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(k); setSortDir("desc"); }
  };

  const roleOf = (p: Paper): "seed" | "foundational" | "cited" => {
    if (p.paper_id === run.seed_paper_id) return "seed";
    if (foundationalSet.has(p.paper_id)) return "foundational";
    return "cited";
  };

  return (
    <div className="space-y-5">
      {/* Filters */}
      <div className="glass rounded-2xl p-4 flex flex-col lg:flex-row lg:items-center gap-3">
        <div className="flex items-center gap-2 px-3 h-10 rounded-xl bg-surface-strong/60 border border-border flex-1 min-w-0">
          <Search className="h-4 w-4 text-text-muted shrink-0" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search title, author, journal, DOI…"
            className="bg-transparent outline-none text-sm text-text-primary placeholder:text-text-muted w-full"
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Toggle active={seedOnly} onClick={() => setSeedOnly(!seedOnly)}>Seed only</Toggle>
          <Toggle active={hasDoiOnly} onClick={() => setHasDoiOnly(!hasDoiOnly)}>Has DOI</Toggle>
          <span className="text-xs text-text-muted ml-2">{rows.length} papers</span>
        </div>
      </div>

      {/* Table */}
      {rows.length === 0 ? (
        <EmptyState title="No papers match your filters" description="Try clearing search or filters." />
      ) : (
        <div className="glass rounded-2xl overflow-hidden">
          <div className="hidden md:grid grid-cols-[1fr_80px_180px_180px_120px_120px_140px] gap-3 px-4 py-3 border-b border-border text-[11px] uppercase tracking-wider text-text-muted font-semibold">
            <SortHeader label="Title" k="title" sortKey={sortKey} dir={sortDir} onClick={toggleSort} />
            <SortHeader label="Year" k="year" sortKey={sortKey} dir={sortDir} onClick={toggleSort} />
            <span>Journal</span>
            <span>Authors</span>
            <SortHeader label="Citations" k="citations" sortKey={sortKey} dir={sortDir} onClick={toggleSort} />
            <SortHeader label="Confidence" k="confidence" sortKey={sortKey} dir={sortDir} onClick={toggleSort} />
            <span>Role</span>
          </div>
          <div className="divide-y divide-border max-h-[70vh] overflow-y-auto scrollbar-thin">
            {rows.map((p) => {
              const isSeed = p.paper_id === run.seed_paper_id;
              return (
                <button
                  key={p.paper_id}
                  onClick={() => setSelected(p)}
                  className={`w-full text-left grid grid-cols-1 md:grid-cols-[1fr_80px_180px_180px_120px_120px_140px] gap-3 px-4 py-3.5 hover:bg-surface-hover/40 transition-colors ${isSeed ? "bg-gradient-to-r from-indigo/10 to-cyan/5 border-l-2 border-l-cyan" : ""}`}
                >
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-text-primary leading-snug">{truncateTitle(p.title, 110)}</div>
                    {p.doi && <div className="text-[11px] text-text-muted font-mono mt-0.5 truncate">{p.doi}</div>}
                  </div>
                  <div className="text-sm text-text-secondary">{p.year ?? "—"}</div>
                  <div className="text-sm text-text-secondary truncate italic">{p.journal ?? "—"}</div>
                  <div className="text-sm text-text-secondary truncate">{formatAuthors(p.authors)}</div>
                  <div className="text-sm text-text-secondary font-mono">{formatNumber(p.citation_count)}</div>
                  <div><ConfidenceBadge score={p.metadata_confidence} /></div>
                  <div><RoleBadge role={roleOf(p)} /></div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      <PaperDetailDrawer paper={selected} run={run} onClose={() => setSelected(null)} />
    </div>
  );
}

function Toggle({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 h-9 rounded-lg text-xs font-semibold border transition-colors ${active ? "gradient-brand-soft text-text-primary border-indigo/40" : "bg-surface-strong/60 text-text-secondary border-border hover:bg-surface-hover"}`}
    >
      {children}
    </button>
  );
}

function SortHeader({ label, k, sortKey, dir, onClick }: { label: string; k: SortKey; sortKey: SortKey; dir: "asc" | "desc"; onClick: (k: SortKey) => void }) {
  const active = sortKey === k;
  return (
    <button onClick={() => onClick(k)} className={`flex items-center gap-1 hover:text-text-primary transition-colors ${active ? "text-cyan" : ""}`}>
      {label}
      <ArrowUpDown className="h-3 w-3" />
      {active && <span className="text-[10px]">{dir === "asc" ? "↑" : "↓"}</span>}
    </button>
  );
}
