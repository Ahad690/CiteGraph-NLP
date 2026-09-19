import { createFileRoute } from "@tanstack/react-router";
import { DashboardRoute } from "@/components/layout/DashboardRoute";
import { PopulationPage } from "@/components/dashboard/PopulationPage";

export const Route = createFileRoute("/population/$runId")({
  component: () => {
    const { runId } = Route.useParams();
    return <DashboardRoute runId={runId} title="Evidence Extraction" subtitle="Clinical populations and technical dataset counts" render={(run) => <PopulationPage run={run} />} />;
  },
});
