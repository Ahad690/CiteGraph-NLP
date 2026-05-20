import { createFileRoute } from "@tanstack/react-router";
import { DashboardRoute } from "@/components/layout/DashboardRoute";
import { MetadataPage } from "@/components/dashboard/MetadataPage";

export const Route = createFileRoute("/metadata/$runId")({
  component: () => {
    const { runId } = Route.useParams();
    return <DashboardRoute runId={runId} title="Metadata" subtitle="All resolved papers in the citation network" render={(run) => <MetadataPage run={run} />} />;
  },
});
