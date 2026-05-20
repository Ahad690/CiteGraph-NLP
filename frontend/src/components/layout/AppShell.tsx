import type { ReactNode } from "react";
import { Toaster } from "sonner";
import { Sidebar } from "./Sidebar";
import { TopHeader } from "./TopHeader";
import { useRun } from "@/hooks/useRun";
import { ErrorState } from "../ui-kit/ErrorState";
import { Menu } from "lucide-react";
import { useState } from "react";
import { Link } from "@tanstack/react-router";

interface Props {
  runId: string | null;
  title: string;
  subtitle?: string;
  children: (run: ReturnType<typeof useRun>) => ReactNode;
}

export function AppShell({ runId, title, subtitle, children }: Props) {
  const run = useRun(runId);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen flex bg-background">
      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-black/60" onClick={() => setMobileOpen(false)} />
          <div className="relative">
            <Sidebar runId={runId} run={run.data} loading={run.isLoading} />
          </div>
        </div>
      )}

      <Sidebar runId={runId} run={run.data} loading={run.isLoading} />

      <div className="flex-1 min-w-0 flex flex-col">
        <div className="lg:hidden flex items-center justify-between px-4 h-14 border-b border-border glass">
          <Link to="/" className="flex items-center gap-2 font-semibold text-sm">
            <span className="h-7 w-7 rounded-lg gradient-brand grid place-items-center text-white text-xs">CG</span>
            CiteGraph-NLP
          </Link>
          <button onClick={() => setMobileOpen(true)} className="h-9 w-9 grid place-items-center rounded-lg border border-border">
            <Menu className="h-4 w-4" />
          </button>
        </div>

        <TopHeader title={title} subtitle={subtitle} runId={runId} run={run.data} />

        <main className="flex-1 px-4 lg:px-8 py-6 lg:py-8 max-w-[1600px] w-full mx-auto">
          {run.isError ? (
            <ErrorState
              title="Failed to load run"
              message={(run.error as Error)?.message || "Backend may be unavailable."}
              runId={runId}
              onRetry={() => run.refetch()}
            />
          ) : (
            children(run)
          )}
        </main>
      </div>

      <Toaster position="bottom-right" theme="dark" richColors closeButton />
    </div>
  );
}
