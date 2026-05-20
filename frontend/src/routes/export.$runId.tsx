import { createFileRoute } from "@tanstack/react-router";
import { DashboardRoute } from "@/components/layout/DashboardRoute";
import { ExportPage } from "@/components/dashboard/ExportPage";

export const Route = createFileRoute("/export/$runId")({
  component: () => {
    const { runId } = Route.useParams();
    return <DashboardRoute runId={runId} title="Export Report" subtitle="Download analysis outputs" render={(run) => <ExportPage run={run} />} />;
  },
});
