import { createFileRoute } from "@tanstack/react-router";
import { DashboardRoute } from "@/components/layout/DashboardRoute";
import { RankingsPage } from "@/components/dashboard/RankingsPage";

export const Route = createFileRoute("/rankings/$runId")({
  component: () => {
    const { runId } = Route.useParams();
    return <DashboardRoute runId={runId} title="Foundational Rankings" subtitle="Probable foundational papers — evidence-weighted" render={(run) => <RankingsPage run={run} />} />;
  },
});
