import { createFileRoute } from "@tanstack/react-router";
import { DashboardRoute } from "@/components/layout/DashboardRoute";
import { CitationPathsPage } from "@/components/dashboard/CitationPathsPage";

export const Route = createFileRoute("/paths/$runId")({
  component: () => {
    const { runId } = Route.useParams();
    return <DashboardRoute runId={runId} title="Citation Paths" subtitle="Ranked lineage from seed paper to older studies" render={(run) => <CitationPathsPage run={run} />} />;
  },
});
