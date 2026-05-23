import { Activity, AlertTriangle } from "lucide-react";
import type { RunPayload } from "@/types/api";
import { formatRelativeTime, truncateTitle } from "@/lib/formatters";
import { deriveStatus, isCompletedRunResult, userFacingError } from "@/lib/runNormalization";
import { StatusBadge } from "../ui-kit/StatusBadge";

interface Props {
  runId: string | null;
  /** Raw query payload — may be either a completed RunResult or a
   *  RunStatusPayload (in-progress / failed). Either is handled here. */
  run?: RunPayload;
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

  const status = run ? deriveStatus(run) : undefined;
  const isProcessing = !!status && ["pending", "running", "processing", "started"].includes(status);
  const isFailed = status === "failed";
  const isCompleted = !!run && isCompletedRunResult(run);
  // Only completed runs carry papers/seed_paper_id.
  const seedPaper = isCompleted
    ? run.papers.find((p) => p.paper_id === run.seed_paper_id)
    : undefined;
  const rawError = !isCompleted ? (run as { error?: string | null } | undefined)?.error ?? null : null;

  return (
    <div className="rounded-2xl bg-surface-strong/70 border border-border p-3.5 space-y-2.5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div
            className={`h-2 w-2 rounded-full ${
              isProcessing
                ? "bg-amber animate-pulse"
                : status === "completed"
                ? "bg-emerald"
                : isFailed
                ? "bg-rose"
                : "bg-text-muted"
            }`}
          />
          <code className="text-[11px] text-text-secondary truncate font-mono">{runId}</code>
        </div>
        {status && <StatusBadge status={status} small />}
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
      ) : isFailed ? (
        <div>
          <div className="text-[11px] uppercase tracking-wider text-rose font-semibold mb-1 flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" /> Analysis failed
          </div>
          <div className="text-[12px] text-text-secondary leading-snug">
            {userFacingError(rawError, runId).message}
          </div>
        </div>
      ) : isProcessing ? (
        <div>
          <div className="text-[11px] uppercase tracking-wider text-text-muted font-semibold mb-1 flex items-center gap-1">
            <Activity className="h-3 w-3" /> In progress
          </div>
          <div className="text-[12px] text-text-secondary leading-snug">
            Fetching metadata, traversing citations, and extracting evidence…
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
