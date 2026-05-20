import { Activity } from "lucide-react";
import type { RunResult } from "@/types/api";
import { formatRelativeTime, truncateTitle } from "@/lib/formatters";
import { StatusBadge } from "../ui-kit/StatusBadge";

interface Props {
  runId: string | null;
  run?: RunResult;
  loading?: boolean;
}

export function RunStatusCard({ runId, run, loading }: Props) {
  if (!runId) {
    return (
      <div className="rounded-2xl border border-dashed border-border/80 bg-surface-strong/40 p-3">
        <div className="text-[11px] uppercase tracking-wider text-text-muted font-semibold">No active run</div>
        <div className="text-xs text-text-muted mt-1">Start an analysis to view results.</div>
      </div>
    );
  }

  const seedPaper = run?.papers.find((p) => p.paper_id === run.seed_paper_id);
  const isProcessing = run && ["pending", "running", "processing", "started"].includes(run.status);

  return (
    <div className="rounded-2xl bg-surface-strong/70 border border-border p-3.5 space-y-2.5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className={`h-2 w-2 rounded-full ${isProcessing ? "bg-amber animate-pulse" : run?.status === "completed" ? "bg-emerald" : run?.status === "failed" ? "bg-rose" : "bg-text-muted"}`} />
          <code className="text-[11px] text-text-secondary truncate font-mono">{runId}</code>
        </div>
        {run && <StatusBadge status={run.status} small />}
      </div>

      {loading && !run ? (
        <div className="space-y-2">
          <div className="skeleton h-3 w-full" />
          <div className="skeleton h-3 w-2/3" />
        </div>
      ) : seedPaper ? (
        <div>
          <div className="text-[11px] uppercase tracking-wider text-text-muted font-semibold mb-1 flex items-center gap-1">
            <Activity className="h-3 w-3" /> Seed paper
          </div>
          <div className="text-[12.5px] text-text-primary leading-snug font-medium">
            {truncateTitle(seedPaper.title, 78)}
          </div>
        </div>
      ) : null}

      {run && (
        <div className="text-[11px] text-text-muted">Updated {formatRelativeTime(run.created_at)}</div>
      )}

      {isProcessing && (
        <div className="h-1 w-full rounded-full bg-surface-hover overflow-hidden">
          <div className="h-full w-1/3 gradient-brand animate-pulse rounded-full" />
        </div>
      )}
    </div>
  );
}
