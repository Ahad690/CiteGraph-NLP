import { createFileRoute } from "@tanstack/react-router";
import { DashboardRoute } from "@/components/layout/DashboardRoute";
import { PopulationPage } from "@/components/dashboard/PopulationPage";

export const Route = createFileRoute("/population/$runId")({
  component: () => {
    const { runId } = Route.useParams();
    return <DashboardRoute runId={runId} title="Population Extraction" subtitle="Confidence-aware extraction with visible uncertainty" render={(run) => <PopulationPage run={run} />} />;
  },
});
