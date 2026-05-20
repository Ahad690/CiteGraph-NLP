import { createFileRoute, Navigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { getActiveRunId } from "@/lib/api";
import { EmptyState } from "@/components/ui-kit/EmptyState";
import { Sparkles } from "lucide-react";
import { z } from "zod";

export const Route = createFileRoute("/dashboard/")({
  validateSearch: z.object({ run_id: z.string().optional() }),
  component: DashboardIndex,
});

function DashboardIndex() {
  const search = Route.useSearch();
  const [storedId, setStoredId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => { setStoredId(getActiveRunId()); setReady(true); }, []);

  const runId = search.run_id || storedId;
  if (!ready) return null;
  if (runId) return <Navigate to="/dashboard/$runId" params={{ runId }} replace />;

  return (
    <div className="min-h-screen grid place-items-center px-6 py-10">
      <EmptyState
        icon={<Sparkles className="h-6 w-6 text-cyan" />}
        title="No analysis run selected"
        description="Start an analysis first to view citation lineage results."
        action={{ label: "Start New Analysis", to: "/start" }}
      />
    </div>
  );
}
