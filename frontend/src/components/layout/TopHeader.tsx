import { useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { RefreshCw, Download, Search } from "lucide-react";
import { StatusBadge } from "../ui-kit/StatusBadge";
import type { RunResult } from "@/types/api";

interface TopHeaderProps {
  title: string;
  subtitle?: string;
  runId: string | null;
  run?: RunResult;
}

export function TopHeader({ title, subtitle, runId, run }: TopHeaderProps) {
  const qc = useQueryClient();

  return (
    <header className="sticky top-0 z-30 h-[76px] glass border-b border-border/60">
      <div className="h-full flex items-center gap-4 lg:gap-6 px-4 lg:px-8">
        <div className="min-w-0 flex-1">
          <h1 className="text-[20px] lg:text-[22px] font-bold tracking-tight text-text-primary truncate">{title}</h1>
          {subtitle && <p className="text-[13px] text-text-muted truncate">{subtitle}</p>}
        </div>

        <div className="hidden xl:flex items-center gap-2 px-3 h-10 rounded-xl bg-surface-strong/60 border border-border min-w-[260px] max-w-[360px]">
          <Search className="h-4 w-4 text-text-muted shrink-0" />
          <input
            placeholder="Search papers, authors, journals…"
            className="bg-transparent border-0 outline-none text-sm text-text-primary placeholder:text-text-muted w-full"
          />
        </div>

        <div className="flex items-center gap-2">
          {run && <StatusBadge status={run.status} />}
          <button
            onClick={() => runId && qc.invalidateQueries({ queryKey: ["run", runId] })}
            className="h-10 w-10 grid place-items-center rounded-xl bg-surface-strong/60 border border-border hover:bg-surface-hover transition-colors"
            aria-label="Refresh"
            title="Refresh run"
          >
            <RefreshCw className="h-4 w-4 text-text-secondary" />
          </button>
          {runId && (
            <Link
              to="/export/$runId"
              params={{ runId }}
              className="hidden md:inline-flex items-center gap-2 h-10 px-4 rounded-xl gradient-brand text-white text-sm font-semibold hover:opacity-95"
            >
              <Download className="h-4 w-4" />
              Export
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
