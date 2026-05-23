import { type ReactNode } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { LoadingSkeleton, CardSkeleton } from "@/components/ui-kit/LoadingSkeleton";
import { useRun } from "@/hooks/useRun";
import type { RunPayload, RunResult, RunStatusPayload } from "@/types/api";
import { normalizeRun, userFacingError } from "@/lib/runNormalization";
import { AlertTriangle } from "lucide-react";
import { Link } from "@tanstack/react-router";

interface Props {
  runId: string;
  title: string;
  subtitle?: string;
  render: (run: RunResult) => ReactNode;
}

export function DashboardRoute({ runId, title, subtitle, render }: Props) {
  return (
    <AppShell runId={runId} title={title} subtitle={subtitle}>
      {(query: ReturnType<typeof useRun>) => {
        if (query.isLoading || !query.data) {
          return (
            <div className="space-y-4">
              <CardSkeleton />
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Array.from({ length: 8 }).map((_, i) => <CardSkeleton key={i} />)}
              </div>
              <LoadingSkeleton rows={6} />
            </div>
          );
        }

        const raw = query.data as unknown as RunPayload;
        const run = normalizeRun(raw);
        const rawError = (raw as RunStatusPayload).error ?? null;

        if (run.status === "failed") {
          const { message, diagnosticId } = userFacingError(rawError, run.run_id);
          return (
            <div className="glass rounded-3xl p-10 text-center max-w-2xl mx-auto">
              <div className="mx-auto h-12 w-12 rounded-2xl bg-rose/10 border border-rose/30 grid place-items-center mb-4">
                <AlertTriangle className="h-6 w-6 text-rose" />
              </div>
              <h3 className="text-lg font-semibold text-text-primary">Analysis failed</h3>
              <p className="text-sm text-text-muted mt-2">{message}</p>
              <p className="text-[11px] text-text-disabled mt-3 font-mono">Run ID: {diagnosticId}</p>
              <Link to="/start" className="inline-flex items-center gap-2 mt-6 px-5 h-10 rounded-xl gradient-brand text-white text-sm font-semibold">
                Try a different paper
              </Link>
            </div>
          );
        }

        const isProcessing = ["pending", "running", "processing", "started"].includes(run.status);
        if (isProcessing && run.papers.length === 0) {
          return (
            <div className="glass rounded-3xl p-10 text-center max-w-2xl mx-auto">
              <div className="mx-auto h-12 w-12 rounded-2xl gradient-brand grid place-items-center mb-4 animate-pulse" />
              <h3 className="text-lg font-semibold text-text-primary">Analysis is still running</h3>
              <p className="text-sm text-text-muted mt-2">Results will appear automatically as they become available.</p>
            </div>
          );
        }
        return render(run);
      }}
    </AppShell>
  );
}
