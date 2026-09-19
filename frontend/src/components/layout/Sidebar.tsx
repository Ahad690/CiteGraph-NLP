import { Link, useRouterState } from "@tanstack/react-router";
import { LayoutDashboard, FileText, Users, Network, GitBranch, Trophy, Download, Sparkles, ArrowUpRight } from "lucide-react";
import { RunStatusCard } from "./RunStatusCard";
import type { RunResult } from "@/types/api";

interface SidebarProps {
  runId: string | null;
  run?: RunResult;
  loading?: boolean;
}

const NAV = [
  { label: "Overview", icon: LayoutDashboard, base: "/dashboard" },
  { label: "Metadata", icon: FileText, base: "/metadata" },
  { label: "Evidence Extraction", icon: Users, base: "/population" },
  { label: "Citation Graph", icon: Network, base: "/graph" },
  { label: "Citation Paths", icon: GitBranch, base: "/paths" },
  { label: "Foundational Rankings", icon: Trophy, base: "/rankings" },
  { label: "Export Report", icon: Download, base: "/export" },
];

export function Sidebar({ runId, run, loading }: SidebarProps) {
  const path = useRouterState({ select: (s) => s.location.pathname });

  return (
    <aside className="hidden lg:flex flex-col w-[280px] shrink-0 h-screen sticky top-0 glass border-r border-border/60">
      <div className="px-5 pt-6 pb-5 border-b border-border/60">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="relative h-10 w-10 rounded-xl gradient-brand grid place-items-center shadow-lg glow-indigo">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="font-bold text-[15px] tracking-tight text-text-primary">CiteGraph-NLP</div>
            <div className="text-[11px] text-text-muted">Research Graph Intelligence</div>
          </div>
        </Link>
      </div>

      <div className="px-4 py-4 border-b border-border/60">
        <RunStatusCard runId={runId} run={run} loading={loading} />
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto scrollbar-thin">
        {NAV.map(({ label, icon: Icon, base }) => {
          const href = runId ? `${base}/${runId}` : base;
          const active = path.startsWith(base);
          return (
            <Link
              key={base}
              to={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-150 ${
                active
                  ? "gradient-brand-soft text-text-primary border border-indigo/30 shadow-[0_0_24px_-6px_rgba(79,70,229,0.45)]"
                  : "text-text-secondary hover:text-text-primary hover:bg-surface-hover/60 border border-transparent"
              }`}
            >
              <Icon className={`h-4 w-4 ${active ? "text-cyan" : ""}`} />
              <span className="font-medium">{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="px-4 py-4 border-t border-border/60 space-y-3">
        <Link
          to="/start"
          className="flex items-center justify-between px-3 py-2.5 rounded-xl gradient-brand text-white text-sm font-semibold hover:opacity-95 transition-opacity"
        >
          <span>Start New Analysis</span>
          <ArrowUpRight className="h-4 w-4" />
        </Link>
        <p className="text-[11px] leading-relaxed text-text-muted px-1">
          Results are confidence-aware estimates. Citation coverage depends on available metadata.
        </p>
      </div>
    </aside>
  );
}
