import { createFileRoute } from "@tanstack/react-router";
import { DashboardRoute } from "@/components/layout/DashboardRoute";
import { OverviewPage } from "@/components/dashboard/OverviewPage";

export const Route = createFileRoute("/dashboard/$runId")({
  component: () => {
    const { runId } = Route.useParams();
    return <DashboardRoute runId={runId} title="Overview" subtitle="Citation lineage estimate at a glance" render={(run) => <OverviewPage run={run} />} />;
  },
});
