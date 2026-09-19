import type { RunResult } from "@/types/api";
import { Link } from "@tanstack/react-router";
import { FileText, Network, Users, Trophy, AlertTriangle, CheckCircle2, Sparkles, Download, GitBranch, ArrowRight } from "lucide-react";
import { StatusBadge } from "@/components/ui-kit/StatusBadge";
import { formatNumber, formatConfidence } from "@/lib/formatters";

export function OverviewPage({ run }: { run: RunResult }) {
  const seed = run.papers.find((p) => p.paper_id === run.seed_paper_id);
  const resolved = run.population_resolutions.filter((r) => r.status === "resolved").length;
  const ambiguous = run.population_resolutions.filter((r) => r.status === "ambiguous" || r.status === "low_confidence").length;
  const missing = run.population_resolutions.filter((r) => r.status === "missing").length;
  const avgConf = run.population_resolutions
    .map((r) => r.confidence)
    .filter((v): v is number => typeof v === "number");
  const avgConfVal = avgConf.length ? avgConf.reduce((a, b) => a + b, 0) / avgConf.length : null;
  const topScore = run.ranked_foundational_papers[0]?.score;
  const hasNoCitationLinks = run.status === "completed" && run.papers.length === 1 && run.citation_edges.length === 0;
  const runYear = new Date(run.created_at).getFullYear();
  const isRecentSeed = seed?.year != null && Number.isFinite(runYear) && seed.year >= runYear - 1 && seed.year <= runYear;

  const stats = [
    { label: "Papers found", value: formatNumber(run.papers.length), icon: FileText, accent: "indigo" },
    { label: "Citation edges", value: formatNumber(run.citation_edges.length), icon: Network, accent: "cyan" },
    { label: "Resolved extractions", value: formatNumber(resolved), icon: CheckCircle2, accent: "emerald" },
    { label: "Ambiguous extractions", value: formatNumber(ambiguous), icon: AlertTriangle, accent: "amber" },
    { label: "Missing population data", value: formatNumber(missing), icon: Users, accent: "muted" },
    { label: "Avg. confidence", value: avgConfVal != null ? formatConfidence(avgConfVal) : "—", icon: Sparkles, accent: "purple" },
    { label: "Top foundational score", value: topScore != null ? formatConfidence(topScore) : "—", icon: Trophy, accent: "indigo" },
    { label: "Warnings", value: formatNumber(run.warnings.length), icon: AlertTriangle, accent: "rose" },
  ];

  const pipeline = [
    { label: "Metadata resolved", done: run.papers.length > 0 },
    { label: "Citations retrieved", done: run.citation_edges.length > 0 },
    { label: "Population evidence extracted", done: run.population_resolutions.length > 0 },
    { label: "Knowledge graph built", done: run.citation_edges.length > 0 && run.papers.length > 1 },
    { label: "Rankings calculated", done: run.ranked_foundational_papers.length > 0 },
  ];

  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-3xl glass border border-border p-6 lg:p-8">
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full gradient-brand opacity-20 blur-3xl" />
        <div className="relative">
          <div className="flex items-center gap-2 mb-3">
            <span className="label-tiny">Run {run.run_id}</span>
            <StatusBadge status={run.status} small />
          </div>
          <h1 className="text-[28px] lg:text-[34px] font-bold tracking-tight text-text-primary">Citation Lineage Overview</h1>
          <p className="text-sm lg:text-base text-text-secondary mt-2 max-w-2xl">
            Confidence-aware map of papers, population evidence, and probable foundational studies.
          </p>
          {seed && (
            <div className="mt-5 rounded-2xl bg-surface-strong/50 border border-border p-4 max-w-3xl">
              <div className="label-tiny mb-1.5">Seed paper</div>
              <div className="font-semibold text-text-primary">{seed.title}</div>
              <div className="text-xs text-text-muted mt-1">{seed.year} · {seed.journal}</div>
            </div>
          )}
        </div>
      </div>

      {hasNoCitationLinks && (
        <div role="note" className="rounded-2xl bg-amber/10 border border-amber/30 p-4 text-sm text-amber flex items-start gap-3">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <div>
            <div className="font-semibold">No citation links available</div>
            <p className="mt-1">This run found no usable reference or citing-paper links for the seed paper. {isRecentSeed ? "This is a recent paper, so citation indexing may improve over time." : "Metadata-provider coverage may be incomplete; try again later or check the paper's reference list."}</p>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 lg:gap-4">
        {stats.map((s) => (
          <div key={s.label} className="glass rounded-2xl p-4 hover:border-border-strong transition-colors">
            <div className="flex items-center justify-between">
              <span className="label-tiny">{s.label}</span>
              <s.icon className="h-4 w-4 text-text-muted" />
            </div>
            <div className="text-2xl lg:text-[28px] font-bold text-text-primary mt-2">{s.value}</div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        {/* Pipeline */}
        <div className="lg:col-span-2 glass rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-text-primary">Pipeline progress</h3>
            <StatusBadge status={run.status} small />
          </div>
          <div className="space-y-3">
            {pipeline.map((p) => (
              <div key={p.label} className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-surface-strong/40 border border-border">
                <div className={`h-7 w-7 rounded-lg grid place-items-center ${p.done ? "bg-emerald/15 text-emerald border border-emerald/30" : "bg-surface-hover text-text-muted border border-border"}`}>
                  {p.done ? <CheckCircle2 className="h-4 w-4" /> : <span className="h-2 w-2 rounded-full bg-current animate-pulse" />}
                </div>
                <div className="flex-1 text-sm text-text-secondary">{p.label}</div>
                <span className={`text-[11px] font-semibold ${p.done ? "text-emerald" : "text-text-muted"}`}>{p.done ? "Completed" : "Pending"}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Warnings */}
        <div className="glass rounded-2xl p-5">
          <h3 className="text-base font-semibold text-text-primary mb-4">Warnings</h3>
          {run.warnings.length === 0 ? (
            <div className="rounded-xl bg-emerald/10 border border-emerald/30 p-4 text-sm text-emerald flex items-start gap-2">
              <CheckCircle2 className="h-4 w-4 mt-0.5" />
              <span>No provider warnings were reported.</span>
            </div>
          ) : (
            <div className="space-y-2">
              {run.warnings.map((w, i) => (
                <div key={i} className="rounded-xl bg-amber/10 border border-amber/30 p-3 text-xs text-amber flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                  <span>{w}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Quick actions */}
      <div>
        <h3 className="text-base font-semibold text-text-primary mb-3">Continue exploring</h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
          <QuickCard to={`/metadata/${run.run_id}`} icon={FileText} title="View metadata" desc="All papers, authors, journals" />
          <QuickCard to={`/population/${run.run_id}`} icon={Users} title="Population evidence" desc="Confidence-aware extraction" />
          <QuickCard to={`/graph/${run.run_id}`} icon={Network} title="Citation graph" desc="Interactive visualization" />
          <QuickCard to={`/rankings/${run.run_id}`} icon={Trophy} title="Foundational rankings" desc="Probable foundational papers" />
          <QuickCard to={`/export/${run.run_id}`} icon={Download} title="Export report" desc="JSON, CSV, GraphML, MD" />
        </div>
      </div>
    </div>
  );
}

function QuickCard({ to, icon: Icon, title, desc }: { to: string; icon: typeof FileText; title: string; desc: string }) {
  return (
    <Link to={to} className="group glass rounded-2xl p-4 hover:border-border-strong hover:shadow-[0_20px_40px_-20px_rgba(79,70,229,0.45)] transition-all">
      <div className="flex items-center justify-between mb-3">
        <div className="h-9 w-9 rounded-xl gradient-brand-soft border border-border-strong grid place-items-center">
          <Icon className="h-4 w-4 text-cyan" />
        </div>
        <ArrowRight className="h-4 w-4 text-text-muted group-hover:text-cyan group-hover:translate-x-0.5 transition-all" />
      </div>
      <div className="font-semibold text-sm text-text-primary">{title}</div>
      <div className="text-xs text-text-muted mt-0.5">{desc}</div>
    </Link>
  );
}
