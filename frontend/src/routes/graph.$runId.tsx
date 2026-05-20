import { createFileRoute } from "@tanstack/react-router";
import { DashboardRoute } from "@/components/layout/DashboardRoute";
import { CitationGraphPage } from "@/components/dashboard/CitationGraphPage";

export const Route = createFileRoute("/graph/$runId")({
  component: () => {
    const { runId } = Route.useParams();
    return <DashboardRoute runId={runId} title="Citation Graph" subtitle="Interactive citation lineage visualization" render={(run) => <CitationGraphPage run={run} />} />;
  },
});
